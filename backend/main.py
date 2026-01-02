from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any

import qrcode
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.api import AuthApi, BiliApiClient, BiliApiError
from backend.services.cleaner import CleanerService

app = FastAPI(title="Bilibili Cleaner")


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


def get_auth_headers(
    sessdata: str | None = Header(None, alias="SESSDATA"),
    bili_jct: str | None = Header(None, alias="bili_jct"),
) -> tuple[str, str]:
    if not sessdata or not bili_jct:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing SESSDATA or bili_jct")
    return sessdata, bili_jct


@app.exception_handler(BiliApiError)
async def bilibili_error_handler(_: Request, exc: BiliApiError) -> JSONResponse:
    status_code = exc.status_code or status.HTTP_502_BAD_GATEWAY
    return JSONResponse(
        status_code=status_code,
        content={"error": str(exc), "code": exc.code, "data": exc.data},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.get("/api/qrcode")
async def get_qrcode() -> dict[str, Any]:
    async with BiliApiClient() as client:
        auth = AuthApi(client)
        url, qrcode_key = await auth.generate_qrcode()
    image_b64 = _encode_qrcode(url)
    return {"qrcode_key": qrcode_key, "image": image_b64}


@app.get("/api/qrcode/poll/{qrcode_key}")
async def poll_qrcode(qrcode_key: str) -> dict[str, Any]:
    async with BiliApiClient() as client:
        auth = AuthApi(client)
        data = await auth.poll_qrcode(qrcode_key)
    return {"data": data}


@app.post("/api/clean/followings")
async def clean_followings(
    payload: MidRequest,
    auth: tuple[str, str] = Depends(get_auth_headers),
) -> dict[str, Any]:
    sessdata, bili_jct = auth
    async with BiliApiClient(sessdata=sessdata, bili_jct=bili_jct) as client:
        service = CleanerService(client)
        result = await service.clear_all_followings(payload.mid)
    return {"success": True, "count": result.count}


@app.post("/api/clean/favorites")
async def clean_favorites(
    payload: MidRequest,
    auth: tuple[str, str] = Depends(get_auth_headers),
) -> dict[str, Any]:
    sessdata, bili_jct = auth
    async with BiliApiClient(sessdata=sessdata, bili_jct=bili_jct) as client:
        service = CleanerService(client)
        result = await service.clear_all_favorites(payload.mid)
    return {"success": True, "count": result.count}


@app.post("/api/clean/dynamics")
async def clean_dynamics(
    payload: MidRequest,
    auth: tuple[str, str] = Depends(get_auth_headers),
) -> dict[str, Any]:
    sessdata, bili_jct = auth
    async with BiliApiClient(sessdata=sessdata, bili_jct=bili_jct) as client:
        service = CleanerService(client)
        result = await service.clear_all_dynamics(payload.mid)
    return {"success": True, "count": result.count}


@app.post("/api/clean/history")
async def clean_history(
    auth: tuple[str, str] = Depends(get_auth_headers),
) -> dict[str, Any]:
    sessdata, bili_jct = auth
    async with BiliApiClient(sessdata=sessdata, bili_jct=bili_jct) as client:
        service = CleanerService(client)
        result = await service.clear_history()
    return {"success": True, "count": result.count}


@app.post("/api/clean/comments")
async def clean_comments(
    auth: tuple[str, str] = Depends(get_auth_headers),
) -> dict[str, Any]:
    sessdata, bili_jct = auth
    async with BiliApiClient(sessdata=sessdata, bili_jct=bili_jct) as client:
        service = CleanerService(client)
        result = await service.clear_all_comments()
    return {"success": True, "count": result.count}


@app.post("/api/clean/all")
async def clean_all(
    payload: MidRequest,
    auth: tuple[str, str] = Depends(get_auth_headers),
) -> dict[str, Any]:
    sessdata, bili_jct = auth
    async with BiliApiClient(sessdata=sessdata, bili_jct=bili_jct) as client:
        service = CleanerService(client)
        followings = await service.clear_all_followings(payload.mid)
        favorites = await service.clear_all_favorites(payload.mid)
        dynamics = await service.clear_all_dynamics(payload.mid)
        comments = await service.clear_all_comments()
        history = await service.clear_history()
    total = followings.count + favorites.count + dynamics.count + comments.count + history.count
    return {
        "success": True,
        "counts": {
            "followings": followings.count,
            "favorites": favorites.count,
            "dynamics": dynamics.count,
            "comments": comments.count,
            "history": history.count,
        },
        "total": total,
    }


_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
