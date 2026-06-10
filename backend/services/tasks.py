from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

TaskKind = str
TaskStatus = str  # one of: pending / running / completed / failed / cancelled


@dataclass
class TaskState:
    task_id: str
    kind: TaskKind
    status: TaskStatus = "pending"
    processed: int = 0
    total: int | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    started_at: float | None = None
    finished_at: float | None = None

    def report_progress(self, *, processed: int | None = None, advance: int = 0) -> None:
        if processed is not None:
            self.processed = processed
        elif advance:
            self.processed += advance

    def report_error(self, error: dict[str, Any]) -> None:
        self.errors.append(error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "status": self.status,
            "processed": self.processed,
            "total": self.total,
            "errors": list(self.errors),
            "result": self.result,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


TaskBuilder = Callable[[TaskState], Awaitable[dict[str, Any] | None]]


FINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


class TaskRegistry:
    """In-memory registry of long-running async tasks.

    State lives only in the current process; restart loses progress. Finished
    task history is bounded so a long-running service does not grow forever.
    """

    def __init__(self, *, max_finished: int = 200) -> None:
        self._states: dict[str, TaskState] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._max_finished = max_finished

    def create(
        self,
        kind: TaskKind,
        builder: TaskBuilder,
        *,
        total: int | None = None,
    ) -> TaskState:
        task_id = uuid.uuid4().hex
        state = TaskState(task_id=task_id, kind=kind, total=total)
        self._prune_finished()
        self._states[task_id] = state

        async def runner() -> None:
            state.status = "running"
            state.started_at = time.time()
            try:
                result = await builder(state)
                if isinstance(result, dict):
                    state.result = result
                if state.status == "running":
                    state.status = "completed"
            except asyncio.CancelledError:
                state.status = "cancelled"
                raise
            except Exception as exc:
                state.status = "failed"
                state.errors.append({"type": type(exc).__name__, "message": str(exc)})
                logger.exception("Task %s (%s) failed", task_id, kind)
            finally:
                state.finished_at = time.time()
                self._prune_finished()

        self._tasks[task_id] = asyncio.create_task(runner(), name=f"task-{task_id}")
        return state

    def get(self, task_id: str) -> TaskState | None:
        return self._states.get(task_id)

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    def list_all(self) -> list[TaskState]:
        return list(self._states.values())

    async def wait(self, task_id: str, *, timeout: float | None = None) -> TaskState | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        return self._states.get(task_id)

    def _prune_finished(self) -> None:
        if self._max_finished < 1:
            return
        finished = [
            state
            for state in self._states.values()
            if state.status in FINAL_STATUSES
        ]
        excess = len(finished) - self._max_finished
        if excess <= 0:
            return
        finished.sort(key=lambda state: state.finished_at or state.started_at or 0)
        for state in finished[:excess]:
            task = self._tasks.get(state.task_id)
            if task is not None and not task.done():
                continue
            self._states.pop(state.task_id, None)
            self._tasks.pop(state.task_id, None)


task_registry = TaskRegistry()
