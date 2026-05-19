from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Path, Query

from backend.api import UserApi

from ._deps import AuthDep, authed_client

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{mid}", summary="Get a UP's public profile (WBI signed)")
async def get_user_info(
    mid: int = Path(..., ge=1),
    auth: tuple[str, str] = AuthDep,
) -> dict[str, Any]:
    """Profile fields include ``name``, ``sign``, ``level``, ``face``, etc.

    Note: follower count is **not** here — use ``GET /users/{mid}/stat``.
    """
    async with authed_client(auth) as client:
        api = UserApi(client)
        return await api.get_info(mid)


@router.get("/{mid}/stat", summary="Get a UP's follower/following counts")
async def get_user_stat(
    mid: int = Path(..., ge=1),
    auth: tuple[str, str] = AuthDep,
) -> dict[str, Any]:
    """Returns ``{mid, follower, following, whisper, black}``."""
    async with authed_client(auth) as client:
        api = UserApi(client)
        return await api.get_stat(mid)


@router.get("/{mid}/videos", summary="List a UP's video uploads (WBI signed)")
async def get_user_videos(
    mid: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=50),
    order: str = Query("pubdate", description="pubdate | click | stow"),
    auth: tuple[str, str] = AuthDep,
) -> dict[str, Any]:
    """Returned ``data.list.vlist[].pubdate`` is the upload timestamp.

    Use page=1, page_size=1 to cheaply detect "last upload time" for activity
    filtering at scale.
    """
    async with authed_client(auth) as client:
        api = UserApi(client)
        return await api.get_videos(mid, pn=page, ps=page_size, order=order)
