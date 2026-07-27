from __future__ import annotations

import base64
import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path
from typing import Any

import qrcode
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.api import AuthApi, BiliApiError
from backend.logging_config import configure_logging
from backend.routers import (
    dynamics_router,
    favorites_router,
    followings_router,
    history_router,
    me_router,
    tag_router,
    tasks_router,
    users_router,
)
from backend.routers._deps import anon_client, authed_client, get_auth_headers
from backend.services.cleaner import CleanerService, CleanResult
from backend.services.tasks import TaskCapacityError, task_registry
from backend.settings import settings

configure_logging()
logger = logging.getLogger(__name__)

STARTED_AT = time.time()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Starting Bilibili Cleaner: qps=%.2f timeout=%.1fs retries=%d "
        "max_running_tasks=%d audit_log=%s",
        settings.api_qps,
        settings.http_timeout,
        settings.max_retries,
        settings.max_running_tasks,
        settings.audit_log_path if settings.audit_log_enabled else "disabled",
    )
    try:
        yield
    finally:
        cancelled = await task_registry.shutdown()
        logger.info("Shutdown complete (%s task(s) cancelled)", cancelled)


app = FastAPI(
    lifespan=lifespan,
    title="Bilibili Cleaner",
    version="1.4.0",
    description=(
        "Open-source self-hosted toolkit for inspecting and cleaning your own "
        "Bilibili account: followings, favorite folders, dynamics, and watch "
        "history.\n\n"
        "All requests are rate-limited (default 1.5 r/s, shared per event loop) "
        "and retried with exponential backoff on risk-control responses "
        "(`-352`, `-799`, `-509`, HTTP 412/429) — 3 retries, 4 attempts total. "
        "Long-running cleans are exposed as async tasks under "
        "`/api/v2/tasks/*`.\n\n"
        "Endpoints under `/api/v2/*` are the canonical AI-facing surface; "
        "`/api/clean/*` (v1) are preserved aliases.\n\n"
        "Deletes are permanent — Bilibili has no undo. Only the logged-in "
        "account can be operated on."
    ),
    openapi_tags=[
        {"name": "me", "description": "Identity / session probing"},
        {"name": "users", "description": "Public UP profile + stats + uploads"},
        {"name": "followings", "description": "List, inspect, selectively unfollow"},
        {"name": "favorites", "description": "Folders + items + selective delete"},
        {"name": "dynamics", "description": "Posts list + selective delete"},
        {"name": "history", "description": "Watch history list + delete"},
        {"name": "relation-tags", "description": "Custom following groups (safety net)"},
        {"name": "tasks", "description": "Long-running async task queue"},
        {"name": "v1", "description": "Legacy clear-all endpoints (kept for compatibility)"},
        {"name": "ops", "description": "Health / readiness probes for deployment"},
    ],
)

V2_PREFIX = "/api/v2"
app.include_router(me_router, prefix=V2_PREFIX)
app.include_router(users_router, prefix=V2_PREFIX)
app.include_router(followings_router, prefix=V2_PREFIX)
app.include_router(favorites_router, prefix=V2_PREFIX)
app.include_router(dynamics_router, prefix=V2_PREFIX)
app.include_router(history_router, prefix=V2_PREFIX)
app.include_router(tag_router, prefix=V2_PREFIX)
app.include_router(tasks_router, prefix=V2_PREFIX)


class MidRequest(BaseModel):
    mid: int = Field(..., ge=1)


def _encode_qrcode(data: str) -> str:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Tag each request with an id, then log method / path / status / duration.

    Without this there is no way to correlate a user-reported failure with the
    warnings the services emit, and no visibility into how slow B 站 is being.
    """
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    request.state.request_id = request_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.exception(
            "%s %s failed after %.0fms",
            request.method,
            request.url.path,
            elapsed_ms,
            extra={"request_id": request_id},
        )
        raise
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    if settings.log_requests and not _is_noise(request.url.path):
        logger.info(
            "%s %s -> %s in %.0fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            extra={"request_id": request_id},
        )
    return response


def _is_noise(path: str) -> bool:
    """Health probes and static assets fire constantly and drown the log."""
    return path in {"/healthz", "/readyz"} or path.startswith(("/static", "/assets"))


@app.exception_handler(BiliApiError)
async def bilibili_error_handler(request: Request, exc: BiliApiError) -> JSONResponse:
    status_code = exc.status_code or status.HTTP_502_BAD_GATEWAY
    logger.warning(
        "Upstream Bilibili error on %s: code=%s message=%s",
        request.url.path,
        exc.code,
        exc,
        extra={"request_id": getattr(request.state, "request_id", "-")},
    )
    return JSONResponse(
        status_code=status_code,
        content={"error": str(exc), "code": exc.code, "data": exc.data},
    )


@app.exception_handler(TaskCapacityError)
async def task_capacity_handler(_: Request, exc: TaskCapacityError) -> JSONResponse:
    """Refuse new work rather than piling up concurrent cleans that would all
    contend for the same rate-limit budget and make risk-control more likely."""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": f"Too many tasks running: {exc}",
            "hint": "Wait for a running task to finish, or raise BILI_MAX_RUNNING_TASKS.",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled request failed",
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.get("/healthz", tags=["ops"], summary="Liveness probe")
async def healthz() -> dict[str, Any]:
    """Cheap, unauthenticated, no upstream calls. If this stops answering the
    event loop is wedged and the container should be restarted."""
    return {"status": "ok", "uptime_seconds": round(time.time() - STARTED_AT, 1)}


@app.get("/readyz", tags=["ops"], summary="Readiness / capacity probe")
async def readyz() -> JSONResponse:
    """Reports task-queue saturation. Returns 503 once the queue is full so a
    load balancer stops sending work that would only be rejected with 429.

    Deliberately does not call B 站: a probe running every few seconds would
    consume the shared rate-limit budget and could itself trigger risk control.
    """
    running = task_registry.running_count()
    saturated = running >= settings.max_running_tasks
    body: dict[str, Any] = {
        "status": "saturated" if saturated else "ok",
        "running_tasks": running,
        "max_running_tasks": settings.max_running_tasks,
        "uptime_seconds": round(time.time() - STARTED_AT, 1),
    }
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE if saturated else status.HTTP_200_OK,
        content=body,
    )


@app.get("/api/qrcode", tags=["v1"])
async def get_qrcode() -> dict[str, Any]:
    async with anon_client() as client:
        auth = AuthApi(client)
        url, qrcode_key = await auth.generate_qrcode()
    image_b64 = _encode_qrcode(url)
    return {"qrcode_key": qrcode_key, "image": image_b64}


@app.get("/api/qrcode/poll/{qrcode_key}", tags=["v1"])
async def poll_qrcode(qrcode_key: str) -> dict[str, Any]:
    async with anon_client() as client:
        auth = AuthApi(client)
        data = await auth.poll_qrcode(qrcode_key)
    return {"data": data}


def _v1_response(result: CleanResult) -> dict[str, Any]:
    """Shape a v1 clean response.

    ``success`` now reflects whether the clean actually finished. The extra
    ``errors`` / ``stopped_reason`` fields are additive, so existing callers
    reading ``success`` and ``count`` keep working.
    """
    body: dict[str, Any] = {
        "success": result.complete,
        "count": result.count,
        "errors": result.errors,
    }
    if result.stopped_reason:
        body["stopped_reason"] = result.stopped_reason
    return body


@app.post("/api/clean/followings", tags=["v1"])
async def clean_followings(
    payload: MidRequest,
    auth: tuple[str, str] = Depends(get_auth_headers),
) -> dict[str, Any]:
    async with authed_client(auth) as client:
        service = CleanerService(client)
        result = await service.clear_all_followings(payload.mid)
    return _v1_response(result)


@app.post("/api/clean/favorites", tags=["v1"])
async def clean_favorites(
    payload: MidRequest,
    auth: tuple[str, str] = Depends(get_auth_headers),
) -> dict[str, Any]:
    async with authed_client(auth) as client:
        service = CleanerService(client)
        result = await service.clear_all_favorites(payload.mid)
    return _v1_response(result)


@app.post("/api/clean/dynamics", tags=["v1"])
async def clean_dynamics(
    payload: MidRequest,
    auth: tuple[str, str] = Depends(get_auth_headers),
) -> dict[str, Any]:
    async with authed_client(auth) as client:
        service = CleanerService(client)
        result = await service.clear_all_dynamics(payload.mid)
    return _v1_response(result)


@app.post("/api/clean/history", tags=["v1"])
async def clean_history(
    auth: tuple[str, str] = Depends(get_auth_headers),
) -> dict[str, Any]:
    async with authed_client(auth) as client:
        service = CleanerService(client)
        result = await service.clear_history()
    return _v1_response(result)


@app.post("/api/clean/all", tags=["v1"])
async def clean_all(
    payload: MidRequest,
    auth: tuple[str, str] = Depends(get_auth_headers),
) -> dict[str, Any]:
    async with authed_client(auth) as client:
        service = CleanerService(client)
        followings = await service.clear_all_followings(payload.mid)
        favorites = await service.clear_all_favorites(payload.mid)
        dynamics = await service.clear_all_dynamics(payload.mid)
        history = await service.clear_history()
    parts = {
        "followings": followings,
        "favorites": favorites,
        "dynamics": dynamics,
        "history": history,
    }
    total = sum(part.count for part in parts.values())
    body: dict[str, Any] = {
        "success": all(part.complete for part in parts.values()),
        "counts": {name: part.count for name, part in parts.items()},
        "errors": sum(part.errors for part in parts.values()),
        "total": total,
    }
    stopped = {name: part.stopped_reason for name, part in parts.items() if part.stopped_reason}
    if stopped:
        body["stopped_reason"] = stopped
    return body


_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
