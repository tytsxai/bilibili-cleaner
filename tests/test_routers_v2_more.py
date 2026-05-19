from __future__ import annotations

import httpx
import pytest
import respx

from backend.api.dynamic import DELETE_DYNAMIC_URL, DYNAMICS_URL
from backend.api.favorite import BATCH_DELETE_URL, FOLDERS_URL, RESOURCE_IDS_URL
from backend.api.history import CLEAR_HISTORY_URL
from backend.api.relation import FOLLOWINGS_URL, MODIFY_URL, RELATION_URL
from backend.api.relation_tag import CREATE_TAG_URL, DELETE_TAG_URL, TAG_USERS_URL, UPDATE_TAG_URL
from backend.api.user import RELATION_STAT_URL
from backend.api.wbi import NAV_URL
from backend.services.tasks import task_registry

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


async def test_user_stat(async_client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    with respx.mock() as router:
        router.get(RELATION_STAT_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"follower": 999, "following": 12}}
            )
        )
        resp = await async_client.get("/api/v2/users/5/stat", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["follower"] == 999


async def test_following_detail(async_client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get("https://api.bilibili.com/x/space/wbi/acc/info").mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"mid": 7, "name": "a"}}
            )
        )
        router.get(RELATION_STAT_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"follower": 5}})
        )
        router.get("https://api.bilibili.com/x/space/wbi/arc/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"list": {"vlist": []}, "page": {"count": 0}},
                },
            )
        )
        resp = await async_client.get("/api/v2/followings/7", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["mid"] == 7


async def test_dynamics_list_and_delete(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get(DYNAMICS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"items": []}})
        )
        router.post(DELETE_DYNAMIC_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        listing = await async_client.get("/api/v2/dynamics?mid=10", headers=headers)
        assert listing.status_code == 200
        delete = await async_client.post(
            "/api/v2/dynamics/delete", headers=headers, json={"ids": ["1", "2"]}
        )
        assert delete.status_code == 200
        assert delete.json()["ok"] == 2


async def test_dynamics_clear_task(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get(DYNAMICS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"items": []}})
        )
        resp = await async_client.post(
            "/api/v2/dynamics/clear?mid=10", headers=headers
        )
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]
        await task_registry.wait(task_id, timeout=5)
        info = await async_client.get(f"/api/v2/tasks/{task_id}")
        assert info.json()["status"] == "completed"


async def test_favorites_clear_task(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.get(FOLDERS_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"list": [{"id": 9}]}}
            )
        )
        router.get(RESOURCE_IDS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ids": []}})
        )
        resp = await async_client.post(
            "/api/v2/favorites/clear?mid=10", headers=headers
        )
        task_id = resp.json()["task_id"]
        await task_registry.wait(task_id, timeout=5)
        assert (await async_client.get(f"/api/v2/tasks/{task_id}")).json()["status"] == "completed"


async def test_followings_clear_task(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.get(FOLLOWINGS_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"list": [], "total": 0}}
            )
        )
        resp = await async_client.post(
            "/api/v2/followings/clear?mid=10", headers=headers
        )
        task_id = resp.json()["task_id"]
        await task_registry.wait(task_id, timeout=5)
        assert (await async_client.get(f"/api/v2/tasks/{task_id}")).json()["status"] == "completed"


async def test_history_clear(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.post(CLEAR_HISTORY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        resp = await async_client.post("/api/v2/history/clear", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["success"] is True


async def test_tag_create_delete_rename_list_users(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.post(CREATE_TAG_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"tagid": 9}})
        )
        router.post(DELETE_TAG_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        router.post(UPDATE_TAG_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        router.get(TAG_USERS_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": [{"mid": 1}, {"mid": 2}]}
            )
        )

        c = await async_client.post(
            "/api/v2/relation/tags", headers=headers, json={"name": "test"}
        )
        assert c.status_code == 200

        u = await async_client.put(
            "/api/v2/relation/tags/9",
            headers=headers,
            json={"name": "renamed"},
        )
        assert u.status_code == 200

        listing = await async_client.get(
            "/api/v2/relation/tags/9/users", headers=headers
        )
        assert listing.status_code == 200
        assert len(listing.json()) == 2

        d = await async_client.delete("/api/v2/relation/tags/9", headers=headers)
        assert d.status_code == 200


async def test_relation_get_state_not_exposed_directly_but_followings_endpoint_works(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    # Sanity: confirm that the FollowingService doesn't expose get_following_state
    # as an HTTP endpoint (it's intentionally only on the API layer for now).
    resp = await async_client.get("/api/v2/relation/state/123", headers=headers)
    assert resp.status_code == 404


async def test_tasks_list_endpoint(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/api/v2/tasks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_tasks_cancel(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.delete("/api/v2/tasks/nope")
    assert resp.status_code == 404


async def test_clean_all_task(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get(FOLLOWINGS_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"list": [], "total": 0}}
            )
        )
        router.get(FOLDERS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"list": []}})
        )
        router.get(DYNAMICS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"items": []}})
        )
        router.post(CLEAR_HISTORY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        resp = await async_client.post(
            "/api/v2/tasks/clean-all?mid=10", headers=headers
        )
        task_id = resp.json()["task_id"]
        await task_registry.wait(task_id, timeout=5)
        info = (await async_client.get(f"/api/v2/tasks/{task_id}")).json()
        assert info["status"] == "completed"
        assert info["result"] == {
            "followings": 0,
            "favorites": 0,
            "dynamics": 0,
            "history": 1,
        }
