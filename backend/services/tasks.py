from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from backend.settings import settings

logger = logging.getLogger(__name__)

TaskKind = str
TaskStatus = str  # one of: pending / running / completed / failed / cancelled


class TaskCapacityError(RuntimeError):
    """Raised when too many tasks are already running."""


def owner_key(sessdata: str) -> str:
    """Derive a stable, non-reversible owner id from a session cookie.

    Tasks are keyed by this instead of the raw ``SESSDATA`` so the registry
    never holds a usable credential in memory, and so a task's owner can be
    compared without the value ever appearing in logs or API responses.
    """
    return hashlib.sha256(sessdata.encode("utf-8")).hexdigest()


@dataclass
class TaskState:
    task_id: str
    kind: TaskKind
    owner: str = ""
    status: TaskStatus = "pending"
    processed: int = 0
    total: int | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    result: dict[str, Any] | None = None
    started_at: float | None = None
    finished_at: float | None = None
    max_errors: int = field(default_factory=lambda: settings.max_task_errors)
    error_count: int = 0

    def owned_by(self, owner: str) -> bool:
        """Constant-time owner check. An empty owner means the task predates
        ownership tracking (only reachable in tests) and is treated as public."""
        if not self.owner:
            return True
        return hmac.compare_digest(self.owner, owner)

    def report_progress(self, *, processed: int | None = None, advance: int = 0) -> None:
        if processed is not None:
            self.processed = processed
        elif advance:
            self.processed += advance

    def report_error(self, error: dict[str, Any]) -> None:
        """Record an error, keeping only the first ``max_errors`` entries.

        A clean that fails on every one of tens of thousands of items would
        otherwise pin the whole error list in memory and return it verbatim on
        every status poll. ``error_count`` always reflects the true total.
        """
        self.error_count += 1
        if len(self.errors) < self.max_errors:
            self.errors.append(error)
        elif len(self.errors) == self.max_errors:
            self.errors.append(
                {
                    "type": "Truncated",
                    "message": f"further errors omitted (limit {self.max_errors})",
                }
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "kind": self.kind,
            "status": self.status,
            "processed": self.processed,
            "total": self.total,
            "errors": list(self.errors),
            "error_count": self.error_count,
            "result": self.result,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

    def summary(self) -> dict[str, Any]:
        """Status without the potentially large ``errors`` / ``result`` bodies.

        ``stopped_reason`` is deliberately kept: it is the one field that says
        the clean did not actually finish, and dropping it with the rest of
        ``result`` would make a partial clean indistinguishable from a complete
        one in the task list. It is a short string or a small dict.
        """
        data = self.to_dict()
        data["errors"] = []
        reason = self.result.get("stopped_reason") if isinstance(self.result, dict) else None
        data["result"] = {"stopped_reason": reason} if reason else None
        return data


TaskBuilder = Callable[[TaskState], Awaitable[dict[str, Any] | None]]


FINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})
ACTIVE_STATUSES = frozenset({"pending", "running"})


class TaskRegistry:
    """In-memory registry of long-running async tasks.

    State lives only in the current process; restart loses progress. This is
    why the service must run with a single worker — see ``docs/DEPLOY.md``.
    Finished task history is bounded so a long-running service does not grow
    forever, and concurrent runs are capped so a client cannot queue unbounded
    work against B 站.
    """

    def __init__(
        self,
        *,
        max_finished: int | None = None,
        max_running: int | None = None,
    ) -> None:
        self._states: dict[str, TaskState] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._max_finished = settings.max_finished_tasks if max_finished is None else max_finished
        self._max_running = settings.max_running_tasks if max_running is None else max_running

    def running_count(self) -> int:
        return sum(1 for s in self._states.values() if s.status in ACTIVE_STATUSES)

    def create(
        self,
        kind: TaskKind,
        builder: TaskBuilder,
        *,
        owner: str = "",
        total: int | None = None,
    ) -> TaskState:
        running = self.running_count()
        if running >= self._max_running:
            raise TaskCapacityError(f"{running} tasks already running (limit {self._max_running})")

        task_id = uuid.uuid4().hex
        state = TaskState(task_id=task_id, kind=kind, owner=owner, total=total)
        self._prune_finished()
        self._states[task_id] = state

        async def runner() -> None:
            state.status = "running"
            state.started_at = time.time()
            logger.info("Task %s (%s) started", task_id, kind)
            try:
                result = await builder(state)
                if isinstance(result, dict):
                    state.result = result
                if state.status == "running":
                    state.status = "completed"
                logger.info(
                    "Task %s (%s) %s: processed=%s errors=%s",
                    task_id,
                    kind,
                    state.status,
                    state.processed,
                    state.error_count,
                )
            except asyncio.CancelledError:
                state.status = "cancelled"
                logger.warning(
                    "Task %s (%s) cancelled after processing %s items",
                    task_id,
                    kind,
                    state.processed,
                )
                raise
            except Exception as exc:
                state.status = "failed"
                state.report_error({"type": type(exc).__name__, "message": str(exc)})
                logger.exception("Task %s (%s) failed", task_id, kind)
            finally:
                state.finished_at = time.time()
                self._prune_finished()

        self._tasks[task_id] = asyncio.create_task(runner(), name=f"task-{task_id}")
        return state

    def get(self, task_id: str, *, owner: str | None = None) -> TaskState | None:
        """Look up a task. When ``owner`` is given, a task belonging to someone
        else is reported as missing rather than forbidden — telling a caller
        that a task id exists but isn't theirs leaks that it exists at all."""
        state = self._states.get(task_id)
        if state is None:
            return None
        if owner is not None and not state.owned_by(owner):
            return None
        return state

    def cancel(self, task_id: str, *, owner: str | None = None) -> bool:
        if self.get(task_id, owner=owner) is None:
            return False
        task = self._tasks.get(task_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    def list_all(self, *, owner: str | None = None) -> list[TaskState]:
        states = self._states.values()
        if owner is None:
            return list(states)
        return [state for state in states if state.owned_by(owner)]

    async def wait(self, task_id: str, *, timeout: float | None = None) -> TaskState | None:
        """Wait for a task to finish, then return its state.

        The task's own outcome — including failure — is already recorded on the
        state by the runner, so exceptions raised here are not an error for the
        caller. ``shield`` keeps a timeout from cancelling the underlying work.
        """
        task = self._tasks.get(task_id)
        if task is None:
            return None
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        except (TimeoutError, asyncio.CancelledError):
            pass
        except Exception:
            logger.debug("Task %s finished with an exception", task_id, exc_info=True)
        return self._states.get(task_id)

    async def shutdown(self, *, grace: float | None = None) -> int:
        """Cancel every in-flight task and wait briefly for them to unwind.

        Without this, SIGTERM tears the event loop down mid-delete and the task
        state is lost while still reading ``running`` — the operator has no way
        to tell how far a clean got. Returns the number of tasks cancelled.
        """
        pending = [(task_id, task) for task_id, task in self._tasks.items() if not task.done()]
        if not pending:
            return 0

        logger.warning("Shutting down with %s task(s) still running; cancelling", len(pending))
        for task_id, task in pending:
            logger.warning(
                "Cancelling task %s (%s), processed=%s",
                task_id,
                self._states[task_id].kind if task_id in self._states else "?",
                self._states[task_id].processed if task_id in self._states else "?",
            )
            task.cancel()

        timeout = settings.shutdown_grace_seconds if grace is None else grace
        try:
            await asyncio.wait_for(
                asyncio.gather(*(task for _, task in pending), return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.error("Task(s) did not stop within %.1fs of shutdown", timeout)

        # A task killed before its handler ran would otherwise stay "running".
        for task_id, _ in pending:
            state = self._states.get(task_id)
            if state is not None and state.status not in FINAL_STATUSES:
                state.status = "cancelled"
                state.finished_at = state.finished_at or time.time()
        return len(pending)

    def _prune_finished(self) -> None:
        if self._max_finished < 1:
            return
        finished = [state for state in self._states.values() if state.status in FINAL_STATUSES]
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


def reset_for_tests() -> None:
    """Clear registry state between tests so capacity limits don't leak."""
    task_registry._states.clear()
    task_registry._tasks.clear()
