from __future__ import annotations

import asyncio

import pytest

from backend.services.tasks import TaskRegistry, TaskState

pytestmark = pytest.mark.asyncio


async def test_create_and_complete_task() -> None:
    registry = TaskRegistry()

    async def runner(state: TaskState) -> dict:
        for _ in range(3):
            state.report_progress(advance=1)
            await asyncio.sleep(0)
        return {"done": True}

    state = registry.create("test", runner, total=3)
    await registry.wait(state.task_id)
    final = registry.get(state.task_id)
    assert final is not None
    assert final.status == "completed"
    assert final.processed == 3
    assert final.result == {"done": True}
    assert final.started_at is not None
    assert final.finished_at is not None


async def test_failed_task_captures_error() -> None:
    registry = TaskRegistry()

    async def runner(state: TaskState) -> dict:
        raise RuntimeError("boom")

    state = registry.create("test", runner)
    await registry.wait(state.task_id)
    final = registry.get(state.task_id)
    assert final is not None
    assert final.status == "failed"
    assert any(e["message"] == "boom" for e in final.errors)


async def test_cancel_task() -> None:
    registry = TaskRegistry()

    async def runner(state: TaskState) -> dict:
        await asyncio.sleep(10)
        return {"done": True}

    state = registry.create("test", runner)
    await asyncio.sleep(0)
    assert registry.cancel(state.task_id)
    await registry.wait(state.task_id)
    final = registry.get(state.task_id)
    assert final is not None
    assert final.status == "cancelled"


async def test_cancel_unknown_task() -> None:
    registry = TaskRegistry()
    assert not registry.cancel("does-not-exist")


async def test_list_all() -> None:
    registry = TaskRegistry()

    async def runner(state: TaskState) -> dict:
        return {}

    s1 = registry.create("a", runner)
    s2 = registry.create("b", runner)
    await registry.wait(s1.task_id)
    await registry.wait(s2.task_id)
    ids = {s.task_id for s in registry.list_all()}
    assert {s1.task_id, s2.task_id} <= ids


async def test_to_dict() -> None:
    state = TaskState(task_id="t", kind="x", status="running", processed=5, total=10)
    state.report_error({"message": "e"})
    d = state.to_dict()
    assert d["task_id"] == "t"
    assert d["status"] == "running"
    assert d["processed"] == 5
    assert d["total"] == 10
    assert len(d["errors"]) == 1
