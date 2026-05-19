from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from backend.services import HistoryService

from ._deps import AuthDep, authed_client

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", summary="List watch history (cursor-paginated)")
async def list_history(
    max_id: int = Query(0, description="Cursor: last ``cursor.max`` from previous page"),
    business: str = Query("", description="Filter: archive | pgc | live | ..."),
    view_at: int = Query(0, description="Cursor: last ``cursor.view_at``"),
    page_size: int = Query(20, ge=1, le=30),
    type_: str = Query("all", alias="type"),
    auth: tuple[str, str] = AuthDep,
) -> dict[str, Any]:
    """Returns ``{cursor, list}``. Send ``cursor.max`` + ``cursor.view_at`` as
    the next call's ``max_id`` + ``view_at`` to page through."""
    async with authed_client(auth) as client:
        return await HistoryService(client).list_page(
            max_id=max_id,
            business=business,
            view_at=view_at,
            page_size=page_size,
            type_=type_,
        )


@router.post("/delete", summary="Delete a single history entry by ``kid``")
async def delete_history(
    kid: str = Query(..., description="e.g. ``archive_12345`` or ``pgc_67890``"),
    auth: tuple[str, str] = AuthDep,
) -> dict[str, Any]:
    async with authed_client(auth) as client:
        return await HistoryService(client).delete(kid)


@router.post("/clear", summary="Wipe all watch history (single call, synchronous)")
async def clear_history(auth: tuple[str, str] = AuthDep) -> dict[str, Any]:
    """Unlike other ``/clear`` endpoints this is one B 站 call so we don't
    bother with the task queue."""
    async with authed_client(auth) as client:
        await HistoryService(client).clear()
    return {"success": True, "count": 1}
