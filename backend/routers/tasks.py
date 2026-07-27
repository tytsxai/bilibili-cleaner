from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, status

from backend.schemas import TaskAck, TaskInfo
from backend.services import CleanerService
from backend.services.tasks import TaskState, task_registry

from ._deps import AuthDep, authed_client, task_owner

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", summary="List your tasks (in-memory, without error/result bodies)")
async def list_tasks(auth: tuple[str, str] = AuthDep) -> list[TaskInfo]:
    """Summaries only, scoped to the caller's own session. ``errors`` and
    ``result`` are omitted here because a clean over tens of thousands of items
    would make this response enormous — fetch ``GET /tasks/{task_id}`` for the
    full record."""
    states = task_registry.list_all(owner=task_owner(auth))
    return [TaskInfo(**s.summary()) for s in states]


@router.get(
    "/{task_id}",
    response_model=TaskInfo,
    summary="Get status / progress / errors / result of a task",
)
async def get_task(
    task_id: str = Path(...),
    auth: tuple[str, str] = AuthDep,
) -> TaskInfo:
    state = task_registry.get(task_id, owner=task_owner(auth))
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return TaskInfo(**state.to_dict())


@router.delete(
    "/{task_id}",
    summary="Cancel a running task",
)
async def cancel_task(
    task_id: str = Path(...),
    auth: tuple[str, str] = AuthDep,
) -> dict:
    if not task_registry.cancel(task_id, owner=task_owner(auth)):
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

    async def builder(state: TaskState) -> dict:
        async with authed_client(auth) as client:
            service = CleanerService(client)
            followings = await service.clear_all_followings(mid)
            state.report_progress(advance=followings.count)
            favorites = await service.clear_all_favorites(mid)
            state.report_progress(advance=favorites.count)
            dynamics = await service.clear_all_dynamics(mid)
            state.report_progress(advance=dynamics.count)
            history = await service.clear_history()
            state.report_progress(advance=history.count)
            stopped = {
                name: part.stopped_reason
                for name, part in (
                    ("followings", followings),
                    ("favorites", favorites),
                    ("dynamics", dynamics),
                    ("history", history),
                )
                if part.stopped_reason
            }
            result = {
                "followings": followings.count,
                "favorites": favorites.count,
                "dynamics": dynamics.count,
                "history": history.count,
            }
            if stopped:
                # Surface partial cleans instead of letting the task report
                # "completed" with counts that silently fall short.
                result["stopped_reason"] = stopped
            return result

    state = task_registry.create("clean.all", builder, owner=task_owner(auth))
    return TaskAck(task_id=state.task_id)
