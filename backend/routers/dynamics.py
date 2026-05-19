from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from backend.api import BiliApiClient
from backend.schemas import BatchActionResult, DeleteDynamicsRequest, TaskAck
from backend.services import DynamicService
from backend.services.tasks import TaskState, task_registry

from ._deps import DEFAULT_API_QPS, AuthDep, authed_client

router = APIRouter(prefix="/dynamics", tags=["dynamics"])


@router.get("", summary="List a user's dynamics (one page, cursor-paginated)")
async def list_dynamics(
    mid: int = Query(..., ge=1, description="host_mid"),
    offset: str = Query("", description="Cursor from previous response.offset"),
    auth: tuple[str, str] = AuthDep,
) -> dict[str, Any]:
    """Returned shape: ``{items: [...], has_more, offset}``. WBI-signed under
    the hood. Pass back ``offset`` to fetch the next page until ``has_more=false``."""
    async with authed_client(auth) as client:
        return await DynamicService(client).list_page(mid, offset=offset or None)


@router.post(
    "/delete",
    response_model=BatchActionResult,
    summary="Delete a specific set of dynamic IDs",
)
async def delete_dynamics(
    body: DeleteDynamicsRequest,
    auth: tuple[str, str] = AuthDep,
) -> BatchActionResult:
    async with authed_client(auth) as client:
        result = await DynamicService(client).delete_many(body.ids)
    return BatchActionResult(**result)


@router.post(
    "/clear",
    response_model=TaskAck,
    summary="Delete every dynamic (async task)",
)
async def clear_dynamics_task(
    mid: int = Query(..., ge=1),
    auth: tuple[str, str] = AuthDep,
) -> TaskAck:
    sessdata, bili_jct = auth

    async def builder(state: TaskState) -> dict[str, Any]:
        async with BiliApiClient(
            sessdata=sessdata, bili_jct=bili_jct, qps=DEFAULT_API_QPS
        ) as client:
            service = DynamicService(client)

            def on_item(_id: int, ok: bool, err: dict | None) -> None:
                state.report_progress(advance=1)
                if err is not None:
                    state.report_error(err)

            return await service.clear_all(mid, on_item=on_item)

    state = task_registry.create("dynamics.clear", builder)
    return TaskAck(task_id=state.task_id)
