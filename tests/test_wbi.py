from __future__ import annotations

import httpx
import pytest
import respx

from backend.api.client import BiliApiClient, BiliApiError
from backend.api.wbi import NAV_URL, signed_get

pytestmark = pytest.mark.asyncio

TEST_URL = "https://api.bilibili.com/x/space/wbi/acc/info"

NAV_PAYLOAD = {
    "code": 0,
    "data": {
        "wbi_img": {
            "img_url": "https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b84077c.png",
            "sub_url": "https://i0.hdslb.com/bfs/wbi/4932caff0ff746eab6f01bf08b70ac45.png",
        }
    },
}


@pytest.fixture
async def client() -> BiliApiClient:
    c = BiliApiClient()
    yield c
    await c.close()


async def test_client_caches_wbi_keys(client: BiliApiClient) -> None:
    with respx.mock(assert_all_called=True) as router:
        nav = router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        keys1 = await client.get_wbi_keys()
        keys2 = await client.get_wbi_keys()
        assert keys1 == keys2
        assert nav.call_count == 1  # cached on second call


async def test_invalidate_wbi_keys_refetches(client: BiliApiClient) -> None:
    with respx.mock() as router:
        nav = router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        await client.get_wbi_keys()
        client.invalidate_wbi_keys()
        await client.get_wbi_keys()
        assert nav.call_count == 2


async def test_signed_get_adds_signature(client: BiliApiClient) -> None:
    with respx.mock(assert_all_called=True) as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        route = router.get(TEST_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"mid": 1}})
        )
        payload = await signed_get(client, TEST_URL, {"mid": 1})
        assert payload["data"]["mid"] == 1
        params = route.calls[0].request.url.params
        assert "wts" in params
        assert "w_rid" in params


async def test_signed_get_refreshes_keys_on_wbi_failure(client: BiliApiClient) -> None:
    with respx.mock() as router:
        nav = router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        route = router.get(TEST_URL).mock(
            side_effect=[
                httpx.Response(200, json={"code": -403, "message": "wbi auth"}),
                httpx.Response(200, json={"code": 0, "data": {"mid": 1}}),
            ]
        )
        payload = await signed_get(client, TEST_URL, {"mid": 1})
        assert payload["data"]["mid"] == 1
        assert route.call_count == 2
        assert nav.call_count == 2


async def test_signed_get_propagates_other_errors(client: BiliApiClient) -> None:
    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get(TEST_URL).mock(
            return_value=httpx.Response(200, json={"code": -500, "message": "server"})
        )
        with pytest.raises(BiliApiError) as exc:
            await signed_get(client, TEST_URL, {"mid": 1})
        assert exc.value.code == -500
