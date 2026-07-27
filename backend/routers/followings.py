from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Path, Query

from backend.schemas import (
    BatchActionResult,
    FollowingDetail,
    FollowingListResponse,
    TaskAck,
    UnfollowRequest,
)
from backend.services import FollowingService
from backend.services.tasks import TaskState, task_registry

from ._deps import AuthDep, authed_client, task_owner

router = APIRouter(prefix="/followings", tags=["followings"])


@router.get(
    "",
    response_model=FollowingListResponse,
    summary="List one page of followings (optionally enriched)",
)
async def list_followings(
    mid: int = Query(..., ge=1, description="The owning account's mid"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=50),
    order: str = Query("desc", description="desc | asc"),
    order_type: str = Query("attention", description="attention | (empty) for default"),
    with_detail: bool = Query(
        False, description="Also fetch profile + recent video for each mid (slower)"
    ),
    concurrency: int = Query(3, ge=1, le=10),
    auth: tuple[str, str] = AuthDep,
) -> FollowingListResponse:
    """List followings. When ``with_detail=true``, each item gets an extra
    ``detail`` field with profile + stat + latest video — useful for quality
    filtering. Note: triggers extra requests; respects the global rate limit."""
    async with authed_client(auth) as client:
        service = FollowingService(client)
        data = await service.list_page(
            mid, page=page, page_size=page_size, order=order, order_type=order_type
        )
        items = data.get("list") if isinstance(data, dict) else None
        items_list: list[dict[str, Any]] = (
            [i for i in items if isinstance(i, dict)] if isinstance(items, list) else []
        )
        if with_detail and items_list:
            mids = [int(i["mid"]) for i in items_list if "mid" in i]
            details = await service.enrich(mids, concurrency=concurrency)
            by_mid = {d["mid"]: d for d in details}
            for item in items_list:
                if "mid" in item:
                    item["detail"] = by_mid.get(int(item["mid"]))
        return FollowingListResponse(
            page=page,
            page_size=page_size,
            total=data.get("total") if isinstance(data, dict) else None,
            items=items_list,
        )


@router.get(
    "/{target_mid}",
    response_model=FollowingDetail,
    summary="Get full quality profile of one UP",
)
async def get_following_detail(
    target_mid: int = Path(..., ge=1),
    auth: tuple[str, str] = AuthDep,
) -> FollowingDetail:
    """Combines ``/users/{mid}`` + ``/users/{mid}/stat`` + first video into
    a single shape for quality scoring."""
    async with authed_client(auth) as client:
        service = FollowingService(client)
        detail = await service.get_detail(target_mid)
    return FollowingDetail(**detail)


@router.post(
    "/unfollow",
    response_model=BatchActionResult,
    summary="Unfollow a specific set of mids (synchronous)",
)
async def unfollow_many(
    body: UnfollowRequest,
    auth: tuple[str, str] = AuthDep,
) -> BatchActionResult:
    """Sequentially unfollow each mid (B 站 has no batch endpoint). Subject
    to the global rate limit — long lists (>50) should use
    ``POST /followings/unfollow-task`` instead."""
    async with authed_client(auth) as client:
        service = FollowingService(client)
        result = await service.unfollow_many(body.mids)
    return BatchActionResult(**result)


@router.post(
    "/unfollow-task",
    response_model=TaskAck,
    summary="Unfollow many mids as an async task (returns task_id)",
)
async def unfollow_many_task(
    body: UnfollowRequest,
    auth: tuple[str, str] = AuthDep,
) -> TaskAck:
    """Start a background unfollow. Poll ``GET /tasks/{task_id}`` for progress.

    Recommended for batches >50 since the HTTP client may time out on the
    synchronous endpoint."""
    mids = list(body.mids)

    async def builder(state: TaskState) -> dict[str, Any]:
        async with authed_client(auth) as client:
            service = FollowingService(client)

            def on_item(mid: int, ok: bool, err: dict | None) -> None:
                state.report_progress(advance=1)
                if err is not None:
                    state.report_error(err)

            return await service.unfollow_many(mids, on_item=on_item)

    state = task_registry.create(
        "followings.unfollow", builder, owner=task_owner(auth), total=len(mids)
    )
    return TaskAck(task_id=state.task_id)


@router.post(
    "/clear",
    response_model=TaskAck,
    summary="Unfollow every following (async task)",
)
async def clear_followings_task(
    mid: int = Query(..., ge=1),
    auth: tuple[str, str] = AuthDep,
) -> TaskAck:
    """Background-clear all followings. Equivalent to v1 ``POST /api/clean/followings``
    but returns immediately with a task_id."""
    async def builder(state: TaskState) -> dict[str, Any]:
        async with authed_client(auth) as client:
            service = FollowingService(client)

            def on_item(target: int, ok: bool, err: dict | None) -> None:
                state.report_progress(advance=1)
                if err is not None:
                    state.report_error(err)

            return await service.clear_all(mid, on_item=on_item)

    state = task_registry.create("followings.clear", builder, owner=task_owner(auth))
    return TaskAck(task_id=state.task_id)
