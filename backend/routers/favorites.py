from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Path, Query

from backend.api import BiliApiClient
from backend.schemas import BatchActionResult, DeleteFavoritesRequest, TaskAck
from backend.services import FavoriteService
from backend.services.tasks import TaskState, task_registry

from ._deps import DEFAULT_API_QPS, AuthDep, authed_client

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("/folders", summary="List all favorite folders for the given mid")
async def list_folders(
    mid: int = Query(..., ge=1),
    auth: tuple[str, str] = AuthDep,
) -> list[dict[str, Any]]:
    async with authed_client(auth) as client:
        return await FavoriteService(client).list_folders(mid)


@router.get(
    "/folders/{media_id}/items",
    summary="List items inside a favorite folder",
)
async def list_folder_items(
    media_id: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=40),
    keyword: str = Query(""),
    order: str = Query("mtime", description="mtime | view | pubtime"),
    auth: tuple[str, str] = AuthDep,
) -> dict[str, Any]:
    """Returns ``{info: <folder>, medias: [{id, type, title, bvid, upper, ...}]}``."""
    async with authed_client(auth) as client:
        return await FavoriteService(client).list_items(
            media_id, page=page, page_size=page_size, keyword=keyword, order=order
        )


@router.post(
    "/folders/{media_id}/delete",
    response_model=BatchActionResult,
    summary="Delete specific items from a folder",
)
async def delete_folder_items(
    body: DeleteFavoritesRequest,
    media_id: int = Path(..., ge=1),
    auth: tuple[str, str] = AuthDep,
) -> BatchActionResult:
    async with authed_client(auth) as client:
        result = await FavoriteService(client).delete_resources(
            media_id, [r.model_dump() for r in body.resources]
        )
    return BatchActionResult(**result)


@router.post(
    "/clear",
    response_model=TaskAck,
    summary="Empty every favorite folder (async task)",
)
async def clear_favorites_task(
    mid: int = Query(..., ge=1),
    auth: tuple[str, str] = AuthDep,
) -> TaskAck:
    sessdata, bili_jct = auth

    async def builder(state: TaskState) -> dict[str, Any]:
        async with BiliApiClient(
            sessdata=sessdata, bili_jct=bili_jct, qps=DEFAULT_API_QPS
        ) as client:
            service = FavoriteService(client)

            def on_batch(_media_id: int, batch: list[str], err: dict | None) -> None:
                state.report_progress(advance=len(batch))
                if err is not None:
                    state.report_error(err)

            return await service.clear_all(mid, on_batch=on_batch)

    state = task_registry.create("favorites.clear", builder)
    return TaskAck(task_id=state.task_id)
