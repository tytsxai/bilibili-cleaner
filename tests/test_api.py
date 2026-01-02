from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest
import respx

from backend.api.auth import AuthApi, GENERATE_QRCODE_URL, POLL_QRCODE_URL
from backend.api.client import BiliApiClient, BiliApiError
from backend.api.comment import CommentApi, DELETE_COMMENT_URL
from backend.api.dynamic import DynamicApi, DELETE_DYNAMIC_URL, DYNAMICS_URL
from backend.api.favorite import FavoriteApi, BATCH_DELETE_URL, FOLDERS_URL, RESOURCE_IDS_URL
from backend.api.history import HistoryApi, CLEAR_HISTORY_URL
from backend.api.relation import RelationApi, BATCH_MODIFY_URL, FOLLOWINGS_URL

pytestmark = pytest.mark.asyncio

CSRF_TOKEN = "csrf-token"


@pytest.fixture
async def api_client() -> BiliApiClient:
    client = BiliApiClient(sessdata="sessdata", bili_jct=CSRF_TOKEN)
    yield client
    await client.close()


def parse_form(request: httpx.Request) -> dict[str, list[str]]:
    return parse_qs(request.content.decode())


async def test_client_success(api_client: BiliApiClient) -> None:
    with respx.mock(assert_all_called=True) as router:
        router.get("https://api.bilibili.com/test").mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        payload = await api_client.get("https://api.bilibili.com/test")
        assert payload["data"]["ok"] is True


async def test_client_error_code(api_client: BiliApiClient) -> None:
    with respx.mock() as router:
        router.get("https://api.bilibili.com/error").mock(
            return_value=httpx.Response(200, json={"code": -101, "message": "unauthorized"})
        )
        with pytest.raises(BiliApiError) as exc:
            await api_client.get("https://api.bilibili.com/error")
        assert exc.value.code == -101


async def test_client_missing_code(api_client: BiliApiClient) -> None:
    with respx.mock() as router:
        router.get("https://api.bilibili.com/missing").mock(
            return_value=httpx.Response(200, json={"data": {}})
        )
        with pytest.raises(BiliApiError):
            await api_client.get("https://api.bilibili.com/missing")


async def test_client_invalid_json(api_client: BiliApiClient) -> None:
    with respx.mock() as router:
        router.get("https://api.bilibili.com/invalid").mock(
            return_value=httpx.Response(200, text="not-json")
        )
        with pytest.raises(BiliApiError):
            await api_client.get("https://api.bilibili.com/invalid")


async def test_client_http_error(api_client: BiliApiClient) -> None:
    with respx.mock() as router:
        router.get("https://api.bilibili.com/500").mock(
            return_value=httpx.Response(500, text="error")
        )
        with pytest.raises(BiliApiError) as exc:
            await api_client.get("https://api.bilibili.com/500")
        assert exc.value.status_code == 500


async def test_client_set_cookies() -> None:
    client = BiliApiClient()
    client.set_cookies(sessdata="sess", bili_jct="token")
    assert client.csrf_token == "token"
    await client.close()


async def test_auth_generate_qrcode(api_client: BiliApiClient) -> None:
    auth = AuthApi(api_client)
    with respx.mock(assert_all_called=True) as router:
        router.get(GENERATE_QRCODE_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"url": "https://q", "qrcode_key": "key"}}
            )
        )
        url, key = await auth.generate_qrcode()
        assert url == "https://q"
        assert key == "key"


async def test_auth_generate_qrcode_missing_fields(api_client: BiliApiClient) -> None:
    auth = AuthApi(api_client)
    with respx.mock() as router:
        router.get(GENERATE_QRCODE_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"url": "https://q"}})
        )
        with pytest.raises(BiliApiError):
            await auth.generate_qrcode()


async def test_auth_poll_qrcode(api_client: BiliApiClient) -> None:
    auth = AuthApi(api_client)
    with respx.mock(assert_all_called=True) as router:
        route = router.get(POLL_QRCODE_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"status": 1}})
        )
        data = await auth.poll_qrcode("key")
        assert data["status"] == 1
        request = route.calls[0].request
        assert request.url.params["qrcode_key"] == "key"


async def test_relation_get_followings(api_client: BiliApiClient) -> None:
    api = RelationApi(api_client)
    with respx.mock(assert_all_called=True) as router:
        route = router.get(FOLLOWINGS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"list": [], "total": 0}})
        )
        data = await api.get_followings(123, pn=1, ps=20)
        assert data["total"] == 0
        params = route.calls[0].request.url.params
        assert params["vmid"] == "123"


async def test_relation_batch_unfollow(api_client: BiliApiClient) -> None:
    api = RelationApi(api_client)
    with respx.mock(assert_all_called=True) as router:
        route = router.post(BATCH_MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        data = await api.batch_unfollow([1, 2])
        assert data["ok"] is True
        form = parse_form(route.calls[0].request)
        assert form["fids"] == ["1,2"]
        assert form["act"] == ["2"]


async def test_relation_batch_unfollow_limit(api_client: BiliApiClient) -> None:
    api = RelationApi(api_client)
    with pytest.raises(ValueError):
        await api.batch_unfollow(list(range(51)))


async def test_favorite_get_folders(api_client: BiliApiClient) -> None:
    api = FavoriteApi(api_client)
    with respx.mock(assert_all_called=True) as router:
        router.get(FOLDERS_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"count": 1, "list": [{"id": 1}]}}
            )
        )
        data = await api.get_folders(123)
        assert data["count"] == 1


async def test_favorite_get_folder_ids(api_client: BiliApiClient) -> None:
    api = FavoriteApi(api_client)
    with respx.mock(assert_all_called=True) as router:
        router.get(RESOURCE_IDS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ids": [1, 2, "3"]}})
        )
        ids = await api.get_folder_ids(456)
        assert ids == [1, 2, 3]


async def test_favorite_batch_delete(api_client: BiliApiClient) -> None:
    api = FavoriteApi(api_client)
    with respx.mock(assert_all_called=True) as router:
        route = router.post(BATCH_DELETE_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"success": True}})
        )
        data = await api.batch_delete(789, ["2:1", "2:2"])
        assert data["success"] is True
        form = parse_form(route.calls[0].request)
        assert form["media_id"] == ["789"]


async def test_dynamic_get_dynamics(api_client: BiliApiClient) -> None:
    api = DynamicApi(api_client)
    with respx.mock(assert_all_called=True) as router:
        route = router.get(DYNAMICS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"items": []}})
        )
        data = await api.get_dynamics(321, offset="offset")
        assert data["items"] == []
        params = route.calls[0].request.url.params
        assert params["host_mid"] == "321"


async def test_dynamic_delete_dynamic(api_client: BiliApiClient) -> None:
    api = DynamicApi(api_client)
    with respx.mock(assert_all_called=True) as router:
        route = router.post(DELETE_DYNAMIC_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        data = await api.delete_dynamic(555)
        assert data["ok"] is True
        form = parse_form(route.calls[0].request)
        assert form["dynamic_id"] == ["555"]


async def test_comment_delete_comment(api_client: BiliApiClient) -> None:
    api = CommentApi(api_client)
    with respx.mock(assert_all_called=True) as router:
        route = router.post(DELETE_COMMENT_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        data = await api.delete_comment(1, 999, 888)
        assert data["ok"] is True
        form = parse_form(route.calls[0].request)
        assert form["type"] == ["1"]
        assert form["oid"] == ["999"]
        assert form["rpid"] == ["888"]


async def test_history_clear_history(api_client: BiliApiClient) -> None:
    api = HistoryApi(api_client)
    with respx.mock(assert_all_called=True) as router:
        router.post(CLEAR_HISTORY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        data = await api.clear_history()
        assert data["ok"] is True
