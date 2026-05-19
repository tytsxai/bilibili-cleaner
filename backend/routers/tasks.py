from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, status

from backend.api import BiliApiClient
from backend.schemas import TaskAck, TaskInfo
from backend.services import CleanerService
from backend.services.tasks import TaskState, task_registry

from ._deps import DEFAULT_API_QPS, AuthDep

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", summary="List all known tasks (in-memory)")
async def list_tasks() -> list[TaskInfo]:
    return [TaskInfo(**s.to_dict()) for s in task_registry.list_all()]


@router.get(
    "/{task_id}",
    response_model=TaskInfo,
    summary="Get status / progress / errors / result of a task",
)
async def get_task(task_id: str = Path(...)) -> TaskInfo:
    state = task_registry.get(task_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return TaskInfo(**state.to_dict())


@router.delete(
    "/{task_id}",
    summary="Cancel a running task",
)
async def cancel_task(task_id: str = Path(...)) -> dict:
    if not task_registry.cancel(task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="task not found or already finished",
        )
    return {"cancelled": True}


@router.post(
    "/clean-all",
    response_model=TaskAck,
    summary="Run clear followings + favorites + dynamics + history as one task",
)
async def clean_all_task(
    mid: int,
    auth: tuple[str, str] = AuthDep,
) -> TaskAck:
    """Start a single async task that wipes everything. Poll
    ``GET /tasks/{task_id}`` for progress; ``result`` holds the per-resource
    counts at the end."""
    sessdata, bili_jct = auth

    async def builder(state: TaskState) -> dict:
        async with BiliApiClient(
            sessdata=sessdata, bili_jct=bili_jct, qps=DEFAULT_API_QPS
        ) as client:
            service = CleanerService(client)
            followings = await service.clear_all_followings(mid)
            state.report_progress(advance=followings.count)
            favorites = await service.clear_all_favorites(mid)
            state.report_progress(advance=favorites.count)
            dynamics = await service.clear_all_dynamics(mid)
            state.report_progress(advance=dynamics.count)
            history = await service.clear_history()
            state.report_progress(advance=history.count)
            return {
                "followings": followings.count,
                "favorites": favorites.count,
                "dynamics": dynamics.count,
                "history": history.count,
            }

    state = task_registry.create("clean.all", builder)
    return TaskAck(task_id=state.task_id)
