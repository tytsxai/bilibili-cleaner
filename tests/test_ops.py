"""Tests for the operational surface: health probes, task-queue limits,
graceful shutdown, audit trail, and honest success reporting."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
import respx

from backend import audit
from backend.api import wbi
from backend.api.client import BiliApiClient
from backend.api.relation import FOLLOWINGS_URL, MODIFY_URL
from backend.api.wbi import NAV_URL
from backend.services.dynamic import DynamicService
from backend.services.favorite import FavoriteService
from backend.services.following import FollowingService
from backend.services.tasks import TaskCapacityError, TaskRegistry, TaskState, owner_key
from backend.settings import load_settings

pytestmark = pytest.mark.asyncio


NAV_PAYLOAD = {
    "code": 0,
    "data": {
        "wbi_img": {
            "img_url": "https://i0.hdslb.com/bfs/wbi/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png",
            "sub_url": "https://i0.hdslb.com/bfs/wbi/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.png",
        }
    },
}


@pytest.fixture
def headers() -> dict[str, str]:
    return {"SESSDATA": "sess", "bili_jct": "csrf"}


# --- health probes ---------------------------------------------------------


async def test_healthz_needs_no_auth(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_readyz_reports_capacity(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/readyz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["running_tasks"] == 0
    assert body["max_running_tasks"] >= 1


async def test_requests_carry_a_request_id(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/healthz")
    assert resp.headers.get("X-Request-ID")


async def test_request_id_is_echoed_when_supplied(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/healthz", headers={"X-Request-ID": "trace-me"})
    assert resp.headers["X-Request-ID"] == "trace-me"


# --- task registry limits --------------------------------------------------


async def test_registry_rejects_work_beyond_max_running() -> None:
    registry = TaskRegistry(max_running=1)
    release = asyncio.Event()

    async def blocker(_: TaskState) -> dict:
        await release.wait()
        return {}

    registry.create("test.blocking", blocker)
    with pytest.raises(TaskCapacityError):
        registry.create("test.blocking", blocker)

    release.set()
    await registry.wait(registry.list_all()[0].task_id, timeout=1)


async def test_capacity_error_surfaces_as_429(
    async_client: httpx.AsyncClient, headers: dict[str, str], monkeypatch
) -> None:
    from backend.services import tasks as tasks_module

    monkeypatch.setattr(tasks_module.task_registry, "_max_running", 0)
    resp = await async_client.post("/api/v2/tasks/clean-all?mid=1", headers=headers)
    assert resp.status_code == 429
    assert "Too many tasks" in resp.json()["error"]


async def test_task_errors_are_truncated_but_counted() -> None:
    state = TaskState(task_id="t", kind="test", max_errors=3)
    for index in range(10):
        state.report_error({"index": index})

    assert state.error_count == 10
    # 3 real entries plus one truncation marker.
    assert len(state.errors) == 4
    assert state.errors[-1]["type"] == "Truncated"
    assert state.to_dict()["error_count"] == 10


async def test_list_endpoint_omits_error_and_result_bodies(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    from backend.services.tasks import task_registry

    async def builder(state: TaskState) -> dict:
        state.report_error({"boom": True})
        return {"big": "payload"}

    state = task_registry.create("test.summary", builder)
    await task_registry.wait(state.task_id, timeout=2)

    resp = await async_client.get("/api/v2/tasks", headers=headers)
    entry = next(t for t in resp.json() if t["task_id"] == state.task_id)
    assert entry["errors"] == []
    assert entry["result"] is None
    assert entry["error_count"] == 1

    detail = await async_client.get(f"/api/v2/tasks/{state.task_id}", headers=headers)
    assert detail.json()["result"] == {"big": "payload"}


async def test_task_endpoints_require_auth(async_client: httpx.AsyncClient) -> None:
    assert (await async_client.get("/api/v2/tasks")).status_code == 401
    assert (await async_client.get("/api/v2/tasks/anything")).status_code == 401
    assert (await async_client.delete("/api/v2/tasks/anything")).status_code == 401


# --- graceful shutdown -----------------------------------------------------


async def test_shutdown_cancels_running_tasks_and_marks_state() -> None:
    registry = TaskRegistry(max_running=2)
    started = asyncio.Event()

    async def forever(_: TaskState) -> dict:
        started.set()
        await asyncio.sleep(3600)
        return {}

    state = registry.create("test.forever", forever)
    await asyncio.wait_for(started.wait(), timeout=1)

    cancelled = await registry.shutdown(grace=1.0)

    assert cancelled == 1
    assert state.status == "cancelled"
    assert state.finished_at is not None


async def test_shutdown_is_a_noop_without_running_tasks() -> None:
    assert await TaskRegistry().shutdown(grace=0.1) == 0


# --- audit trail -----------------------------------------------------------


def _audit_entries() -> list[dict]:
    path = Path(audit.settings.audit_log_path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


async def test_unfollow_writes_audit_entries(bili_client: BiliApiClient) -> None:
    with respx.mock() as router:
        router.post(MODIFY_URL).mock(return_value=httpx.Response(200, json={"code": 0}))
        await FollowingService(bili_client).unfollow_many([11, 22])

    entries = _audit_entries()
    assert [e["target"] for e in entries] == [11, 22]
    assert all(e["action"] == "following.unfollow" and e["ok"] for e in entries)


async def test_failed_unfollow_is_audited_with_the_error(bili_client: BiliApiClient) -> None:
    with respx.mock() as router:
        router.post(MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": -101, "message": "not logged in"})
        )
        await FollowingService(bili_client).unfollow_many([11])

    entry = _audit_entries()[0]
    assert entry["ok"] is False
    assert "not logged in" in entry["error"]


async def test_audit_failure_never_breaks_the_clean(
    bili_client: BiliApiClient, monkeypatch
) -> None:
    """An unwritable audit sink must not abort work that is already underway."""
    monkeypatch.setattr(audit, "_initialised", True)
    monkeypatch.setattr(audit, "_sink", None)

    with respx.mock() as router:
        router.post(MODIFY_URL).mock(return_value=httpx.Response(200, json={"code": 0}))
        result = await FollowingService(bili_client).unfollow_many([11])

    assert result["ok"] == 1


# --- honest completion reporting -------------------------------------------


async def test_clear_all_flags_the_page_safety_limit(
    bili_client: BiliApiClient, monkeypatch
) -> None:
    """Hitting the page cap used to be indistinguishable from finishing."""
    monkeypatch.setattr("backend.services.following.MAX_CLEAR_PAGES", 2)

    with respx.mock() as router:
        router.get(FOLLOWINGS_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"list": [{"mid": 7}], "total": 999}}
            )
        )
        router.post(MODIFY_URL).mock(return_value=httpx.Response(200, json={"code": 0}))
        result = await FollowingService(bili_client).clear_all(1)

    assert result["stopped_reason"] == "page_limit"


async def test_dynamic_clear_all_stops_when_a_page_makes_no_progress(
    bili_client: BiliApiClient,
) -> None:
    from backend.api.dynamic import DELETE_DYNAMIC_URL, DYNAMICS_URL

    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get(DYNAMICS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "items": [{"id_str": "100"}, {"id_str": "101"}],
                        "has_more": True,
                        "offset": "next",
                    },
                },
            )
        )
        router.post(DELETE_DYNAMIC_URL).mock(
            return_value=httpx.Response(200, json={"code": -352, "message": "risk"})
        )
        result = await DynamicService(bili_client).clear_all(1)

    assert result["ok"] == 0
    assert result["stopped_reason"] == "no_progress"


async def test_v1_clean_reports_failure_when_items_fail(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.get(FOLLOWINGS_URL).mock(
            side_effect=[
                httpx.Response(200, json={"code": 0, "data": {"list": [{"mid": 7}]}}),
                httpx.Response(200, json={"code": 0, "data": {"list": []}}),
            ]
        )
        router.post(MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": -101, "message": "expired"})
        )
        resp = await async_client.post(
            "/api/clean/followings", json={"mid": 1}, headers=headers
        )

    body = resp.json()
    assert body["success"] is False
    assert body["errors"] == 1
    assert body["stopped_reason"] == "no_progress"


# --- WBI key caching -------------------------------------------------------


async def test_wbi_keys_are_cached_across_clients() -> None:
    """Clients are built per request; without a process-level cache every
    signed call would pay for an extra /nav round trip."""
    with respx.mock() as router:
        route = router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))

        async with BiliApiClient() as first:
            keys = await first.get_wbi_keys()
        async with BiliApiClient() as second:
            assert await second.get_wbi_keys() == keys

        assert route.call_count == 1


async def test_invalidate_clears_the_shared_cache() -> None:
    with respx.mock() as router:
        route = router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))

        async with BiliApiClient() as client:
            await client.get_wbi_keys()
            client.invalidate_wbi_keys()
            await client.get_wbi_keys()

        assert route.call_count == 2
        assert wbi.cached_keys() is not None


# --- settings --------------------------------------------------------------


async def test_settings_fall_back_on_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("BILI_API_QPS", "not-a-number")
    monkeypatch.setenv("BILI_MAX_RETRIES", "-5")
    monkeypatch.setenv("BILI_MAX_RUNNING_TASKS", "9")
    loaded = load_settings()

    assert loaded.api_qps == 1.5
    assert loaded.max_retries == 3
    assert loaded.max_running_tasks == 9


async def test_audit_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("BILI_AUDIT_LOG_ENABLED", "0")
    assert load_settings().audit_log_enabled is False


# --- task ownership --------------------------------------------------------


async def test_owner_key_is_stable_and_not_the_raw_cookie() -> None:
    assert owner_key("sess") == owner_key("sess")
    assert owner_key("sess") != owner_key("other")
    assert "sess" not in owner_key("sess")


async def test_registry_scopes_lookup_and_cancel_to_the_owner() -> None:
    registry = TaskRegistry(max_running=2)

    async def noop(_: TaskState) -> dict:
        return {}

    state = registry.create("test.owned", noop, owner="alice")
    await registry.wait(state.task_id, timeout=2)

    assert registry.get(state.task_id, owner="alice") is not None
    # A different owner must not even learn that the id exists.
    assert registry.get(state.task_id, owner="bob") is None
    assert registry.cancel(state.task_id, owner="bob") is False
    assert [s.task_id for s in registry.list_all(owner="alice")] == [state.task_id]
    assert registry.list_all(owner="bob") == []


async def test_another_session_cannot_see_or_cancel_your_task(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    from backend.services.tasks import task_registry

    async def noop(_: TaskState) -> dict:
        return {}

    state = task_registry.create("test.owned", noop, owner=owner_key(headers["SESSDATA"]))
    await task_registry.wait(state.task_id, timeout=2)

    intruder = {"SESSDATA": "someone-else", "bili_jct": "csrf"}
    assert (
        await async_client.get(f"/api/v2/tasks/{state.task_id}", headers=intruder)
    ).status_code == 404
    assert (
        await async_client.delete(f"/api/v2/tasks/{state.task_id}", headers=intruder)
    ).status_code == 404
    assert (await async_client.get("/api/v2/tasks", headers=intruder)).json() == []

    # The real owner still sees it.
    mine = await async_client.get("/api/v2/tasks", headers=headers)
    assert [t["task_id"] for t in mine.json()] == [state.task_id]


# --- favorites safety guard ------------------------------------------------


async def test_favorite_clear_all_stops_when_a_folder_makes_no_progress(
    bili_client: BiliApiClient,
) -> None:
    from backend.api.favorite import BATCH_DELETE_URL, FOLDERS_URL, RESOURCE_IDS_URL

    with respx.mock() as router:
        router.get(FOLDERS_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"list": [{"id": 1}, {"id": 2}]}}
            )
        )
        router.get(RESOURCE_IDS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ids": [10, 11]}})
        )
        delete_route = router.post(BATCH_DELETE_URL).mock(
            return_value=httpx.Response(200, json={"code": -101, "message": "expired"})
        )
        result = await FavoriteService(bili_client).clear_all(1)

    assert result["ok"] == 0
    assert result["stopped_reason"] == "no_progress"
    # Stopped after the first folder instead of grinding through the second.
    assert delete_route.call_count == 1


# --- partial clean surfaced through the task result ------------------------


async def test_clean_all_task_reports_stopped_reason(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    from backend.api.dynamic import DYNAMICS_URL
    from backend.api.favorite import FOLDERS_URL as FAV_FOLDERS_URL
    from backend.api.history import CLEAR_HISTORY_URL

    with respx.mock(assert_all_called=False) as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        # Followings never drain: every unfollow fails, so the clean must stop.
        router.get(FOLLOWINGS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"list": [{"mid": 7}]}})
        )
        router.post(MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": -101, "message": "expired"})
        )
        router.get(FAV_FOLDERS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"list": []}})
        )
        router.get(DYNAMICS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"items": []}})
        )
        router.post(CLEAR_HISTORY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )

        ack = await async_client.post("/api/v2/tasks/clean-all?mid=1", headers=headers)
        task_id = ack.json()["task_id"]
        from backend.services.tasks import task_registry

        await task_registry.wait(task_id, timeout=5)
        info = (await async_client.get(f"/api/v2/tasks/{task_id}", headers=headers)).json()

    assert info["status"] == "completed"
    assert info["result"]["stopped_reason"] == {"followings": "no_progress"}


# --- background tasks honour the configured client policy ------------------


async def test_background_tasks_use_the_configured_timeout_and_retries(
    async_client: httpx.AsyncClient, headers: dict[str, str], monkeypatch
) -> None:
    """Task builders used to construct their own client and silently skip the
    configured timeout / retry policy — exactly the long runs that need it."""
    from backend.routers import _deps

    captured: dict[str, object] = {}
    original = _deps.build_client

    def spy(auth=None, *, qps=None):
        client = original(auth, qps=qps)
        captured["timeout"] = client._client.timeout.read
        captured["max_retries"] = client._max_retries
        return client

    monkeypatch.setattr(_deps, "build_client", spy)

    with respx.mock(assert_all_called=False) as router:
        router.get(FOLLOWINGS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"list": []}})
        )
        ack = await async_client.post("/api/v2/followings/clear?mid=1", headers=headers)
        from backend.services.tasks import task_registry

        await task_registry.wait(ack.json()["task_id"], timeout=5)

    assert captured["timeout"] == _deps.settings.http_timeout
    assert captured["max_retries"] == _deps.settings.max_retries
