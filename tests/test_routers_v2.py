from __future__ import annotations

import httpx
import pytest
import respx

from backend.services.tasks import task_registry

from backend.api.auth import NAV_URL as AUTH_NAV_URL
from backend.api.favorite import BATCH_DELETE_URL, FOLDERS_URL, RESOURCE_LIST_URL
from backend.api.history import DELETE_HISTORY_URL, HISTORY_CURSOR_URL
from backend.api.relation import FOLLOWINGS_URL, MODIFY_URL
from backend.api.relation_tag import COPY_USERS_URL, LIST_TAGS_URL
from backend.api.user import ACC_INFO_URL, RELATION_STAT_URL
from backend.api.wbi import NAV_URL

pytestmark = pytest.mark.asyncio


@pytest.fixture
def headers() -> dict[str, str]:
    return {"SESSDATA": "sess", "bili_jct": "csrf"}


NAV_PAYLOAD = {
    "code": 0,
    "data": {
        "wbi_img": {
            "img_url": "https://i0.hdslb.com/bfs/wbi/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.png",
            "sub_url": "https://i0.hdslb.com/bfs/wbi/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.png",
        }
    },
}


async def test_me_endpoint(async_client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    with respx.mock() as router:
        router.get(AUTH_NAV_URL).mock(
            return_value=httpx.Response(
                200,
                json={"code": 0, "data": {"isLogin": True, "mid": 42, "uname": "tester"}},
            )
        )
        resp = await async_client.get("/api/v2/me", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["isLogin"] is True
        assert body["mid"] == 42


async def test_me_requires_auth(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/api/v2/me")
    assert resp.status_code == 401


async def test_followings_list(async_client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    with respx.mock() as router:
        router.get(FOLLOWINGS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "list": [{"mid": 1, "uname": "a"}, {"mid": 2, "uname": "b"}],
                        "total": 2,
                    },
                },
            )
        )
        resp = await async_client.get(
            "/api/v2/followings?mid=42&page=1&page_size=20", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 2


async def test_followings_list_with_detail(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get(FOLLOWINGS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"list": [{"mid": 7, "uname": "alice"}], "total": 1},
                },
            )
        )
        router.get(ACC_INFO_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"mid": 7, "name": "alice"}}
            )
        )
        router.get(RELATION_STAT_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"mid": 7, "follower": 99}}
            )
        )
        router.get("https://api.bilibili.com/x/space/wbi/arc/search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "list": {"vlist": [{"bvid": "BV1", "pubdate": 1700000000}]},
                        "page": {"pn": 1, "ps": 1, "count": 3},
                    },
                },
            )
        )
        resp = await async_client.get(
            "/api/v2/followings?mid=42&with_detail=true", headers=headers
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items[0]["detail"]["stat"]["follower"] == 99
        assert items[0]["detail"]["latest_video"]["bvid"] == "BV1"


async def test_followings_unfollow(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.post(MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        resp = await async_client.post(
            "/api/v2/followings/unfollow", headers=headers, json={"mids": [1, 2, 3]}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] == 3
        assert body["errors"] == []


async def test_followings_unfollow_task(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.post(MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        resp = await async_client.post(
            "/api/v2/followings/unfollow-task", headers=headers, json={"mids": [10, 20]}
        )
        assert resp.status_code == 200
        task_id = resp.json()["task_id"]

        await task_registry.wait(task_id, timeout=10)

        poll = await async_client.get(f"/api/v2/tasks/{task_id}")
        final = poll.json()
        assert final["status"] == "completed"
        assert final["result"]["ok"] == 2
        assert final["total"] == 2


async def test_users_endpoints(async_client: httpx.AsyncClient, headers: dict[str, str]) -> None:
    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get(ACC_INFO_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"mid": 5, "name": "u", "sign": "hi"}}
            )
        )
        resp = await async_client.get("/api/v2/users/5", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "u"


async def test_favorites_folders_and_delete(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.get(FOLDERS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"count": 1, "list": [{"id": 9, "title": "default"}]},
                },
            )
        )
        router.get(RESOURCE_LIST_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "info": {"id": 9},
                        "medias": [{"id": 1, "type": 2, "title": "v1"}],
                    },
                },
            )
        )
        router.post(BATCH_DELETE_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )

        folders = await async_client.get("/api/v2/favorites/folders?mid=1", headers=headers)
        assert folders.status_code == 200
        assert folders.json()[0]["id"] == 9

        items = await async_client.get(
            "/api/v2/favorites/folders/9/items", headers=headers
        )
        assert items.status_code == 200

        delete = await async_client.post(
            "/api/v2/favorites/folders/9/delete",
            headers=headers,
            json={"resources": [{"id": 1, "type": 2}]},
        )
        assert delete.status_code == 200
        assert delete.json()["ok"] == 1


async def test_history_list_and_delete(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.get(HISTORY_CURSOR_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"cursor": {"max": 100, "view_at": 1700000000}, "list": []},
                },
            )
        )
        router.post(DELETE_HISTORY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        listing = await async_client.get("/api/v2/history?max_id=0", headers=headers)
        assert listing.status_code == 200
        delete = await async_client.post(
            "/api/v2/history/delete?kid=archive_1", headers=headers
        )
        assert delete.status_code == 200


async def test_tag_endpoints(
    async_client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    with respx.mock() as router:
        router.get(LIST_TAGS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": [{"tagid": 5, "name": "review", "count": 0}],
                },
            )
        )
        router.post(COPY_USERS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )

        tags = await async_client.get("/api/v2/relation/tags", headers=headers)
        assert tags.status_code == 200
        assert tags.json()[0]["name"] == "review"

        members = await async_client.post(
            "/api/v2/relation/tags/members",
            headers=headers,
            json={"mids": [1, 2], "tag_name": "review"},
        )
        assert members.status_code == 200
        body = members.json()
        assert body["tagid"] == 5
        assert body["count"] == 2


async def test_tasks_404(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/api/v2/tasks/does-not-exist")
    assert resp.status_code == 404


async def test_openapi_lists_v2_endpoints(async_client: httpx.AsyncClient) -> None:
    resp = await async_client.get("/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/v2/me" in paths
    assert "/api/v2/followings" in paths
    assert "/api/v2/followings/{target_mid}" in paths
    assert "/api/v2/followings/unfollow" in paths
    assert "/api/v2/relation/tags" in paths
    assert "/api/v2/tasks/{task_id}" in paths
    # v1 preserved
    assert "/api/clean/all" in paths
