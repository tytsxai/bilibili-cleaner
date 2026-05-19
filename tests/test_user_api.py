from __future__ import annotations

import httpx
import pytest
import respx

from backend.api.client import BiliApiClient
from backend.api.user import ACC_INFO_URL, ARC_SEARCH_URL, RELATION_STAT_URL, UserApi
from backend.api.wbi import NAV_URL

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
async def client() -> BiliApiClient:
    c = BiliApiClient()
    yield c
    await c.close()


async def test_get_info_signs_request(client: BiliApiClient) -> None:
    api = UserApi(client)
    with respx.mock(assert_all_called=True) as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        route = router.get(ACC_INFO_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"mid": 1, "name": "x", "sign": "hi"}}
            )
        )
        data = await api.get_info(1)
        assert data["name"] == "x"
        params = route.calls[0].request.url.params
        assert params["mid"] == "1"
        assert "w_rid" in params
        assert "wts" in params


async def test_get_stat(client: BiliApiClient) -> None:
    api = UserApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.get(RELATION_STAT_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"mid": 1, "following": 10, "follower": 99}}
            )
        )
        data = await api.get_stat(1)
        assert data["follower"] == 99
        assert route.calls[0].request.url.params["vmid"] == "1"


async def test_get_videos(client: BiliApiClient) -> None:
    api = UserApi(client)
    with respx.mock(assert_all_called=True) as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        route = router.get(ARC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "list": {"vlist": [{"aid": 1, "bvid": "BV1", "pubdate": 1700000000}]},
                        "page": {"pn": 1, "ps": 30, "count": 1},
                    },
                },
            )
        )
        data = await api.get_videos(1, pn=1, ps=30)
        assert data["list"]["vlist"][0]["bvid"] == "BV1"
        params = route.calls[0].request.url.params
        assert params["mid"] == "1"
        assert params["order"] == "pubdate"
        assert "w_rid" in params
