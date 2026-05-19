from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest
import respx

from backend.api.auth import AuthApi, NAV_URL as AUTH_NAV_URL
from backend.api.client import BiliApiClient
from backend.api.favorite import FavoriteApi, RESOURCE_LIST_URL
from backend.api.history import DELETE_HISTORY_URL, HISTORY_CURSOR_URL, HistoryApi
from backend.api.relation import RELATION_URL, RelationApi, MODIFY_URL

pytestmark = pytest.mark.asyncio
CSRF = "csrf-token"


@pytest.fixture
async def client() -> BiliApiClient:
    c = BiliApiClient(sessdata="sess", bili_jct=CSRF)
    yield c
    await c.close()


def _form(req: httpx.Request) -> dict[str, list[str]]:
    return parse_qs(req.content.decode())


async def test_auth_get_self_info(client: BiliApiClient) -> None:
    api = AuthApi(client)
    with respx.mock(assert_all_called=True) as router:
        router.get(AUTH_NAV_URL).mock(
            return_value=httpx.Response(
                200,
                json={"code": 0, "data": {"isLogin": True, "mid": 12345, "uname": "user"}},
            )
        )
        data = await api.get_self_info()
        assert data["mid"] == 12345


async def test_relation_follow(client: BiliApiClient) -> None:
    api = RelationApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.post(MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        await api.follow(42)
        form = _form(route.calls[0].request)
        assert form["fid"] == ["42"]
        assert form["act"] == ["1"]


async def test_relation_get_following_state(client: BiliApiClient) -> None:
    api = RelationApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.get(RELATION_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"relation": {"status": 2}, "be_relation": {}}}
            )
        )
        data = await api.get_following_state(42)
        assert data["relation"]["status"] == 2
        params = route.calls[0].request.url.params
        assert params["fid"] == "42"


async def test_relation_get_followings_uses_order_params(client: BiliApiClient) -> None:
    api = RelationApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.get("https://api.bilibili.com/x/relation/followings").mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"list": [], "total": 0}})
        )
        await api.get_followings(123, pn=2, ps=30, order="asc", order_type="")
        params = route.calls[0].request.url.params
        assert params["order"] == "asc"
        assert params["pn"] == "2"
        assert params["ps"] == "30"


async def test_favorite_list_resources(client: BiliApiClient) -> None:
    api = FavoriteApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.get(RESOURCE_LIST_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "info": {"id": 9, "title": "default"},
                        "medias": [
                            {"id": 1, "type": 2, "title": "v1", "bvid": "BV1"},
                            {"id": 2, "type": 2, "title": "v2", "bvid": "BV2"},
                        ],
                    },
                },
            )
        )
        data = await api.list_resources(9, pn=1, ps=20)
        assert len(data["medias"]) == 2
        params = route.calls[0].request.url.params
        assert params["media_id"] == "9"
        assert params["pn"] == "1"


async def test_history_list_history(client: BiliApiClient) -> None:
    api = HistoryApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.get(HISTORY_CURSOR_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "cursor": {"max": 100, "view_at": 1700000000},
                        "list": [{"title": "v1"}, {"title": "v2"}],
                    },
                },
            )
        )
        data = await api.list_history(max_id=0, ps=20)
        assert len(data["list"]) == 2
        params = route.calls[0].request.url.params
        assert params["max"] == "0"
        assert params["ps"] == "20"


async def test_history_delete_history(client: BiliApiClient) -> None:
    api = HistoryApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.post(DELETE_HISTORY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        await api.delete_history("archive_12345")
        form = _form(route.calls[0].request)
        assert form["kid"] == ["archive_12345"]
        assert form["csrf"] == [CSRF]
