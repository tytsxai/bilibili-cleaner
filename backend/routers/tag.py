from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Path, Query

from backend.schemas import TagCreateRequest, TagUpdateRequest, TagUsersRequest
from backend.services import TagService

from ._deps import AuthDep, authed_client

router = APIRouter(prefix="/relation/tags", tags=["relation-tags"])


@router.get("", summary="List my custom following groups (tags)")
async def list_tags(auth: tuple[str, str] = AuthDep) -> list[dict[str, Any]]:
    async with authed_client(auth) as client:
        return await TagService(client).list_tags()


@router.post("", summary="Create a new following group")
async def create_tag(
    body: TagCreateRequest,
    auth: tuple[str, str] = AuthDep,
) -> dict[str, Any]:
    async with authed_client(auth) as client:
        return await TagService(client).create_tag(body.name)


@router.delete("/{tagid}", summary="Delete a following group")
async def delete_tag(
    tagid: int = Path(..., ge=0),
    auth: tuple[str, str] = AuthDep,
) -> dict[str, Any]:
    async with authed_client(auth) as client:
        return await TagService(client).delete_tag(tagid)


@router.put("/{tagid}", summary="Rename a following group")
async def rename_tag(
    body: TagUpdateRequest,
    tagid: int = Path(..., ge=0),
    auth: tuple[str, str] = AuthDep,
) -> dict[str, Any]:
    async with authed_client(auth) as client:
        return await TagService(client).rename_tag(tagid, body.name)


@router.post(
    "/members",
    summary="Add mids to a tag (find/create by name if needed)",
)
async def tag_users(
    body: TagUsersRequest,
    auth: tuple[str, str] = AuthDep,
) -> dict[str, Any]:
    """Useful "safety net" workflow: tag suspicious accounts first, audit
    them in B 站's UI, then unfollow after confirming. Pass ``replace=true``
    to remove from other tags."""
    async with authed_client(auth) as client:
        return await TagService(client).tag_users(
            body.mids,
            tagid=body.tagid,
            tag_name=body.tag_name,
            replace=body.replace,
        )


@router.get("/{tagid}/users", summary="List members of a tag")
async def list_tag_users(
    tagid: int = Path(..., ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    auth: tuple[str, str] = AuthDep,
) -> list[dict[str, Any]]:
    async with authed_client(auth) as client:
        return await TagService(client).list_tag_users(
            tagid, page=page, page_size=page_size
        )
