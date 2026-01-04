from __future__ import annotations

import base64
from urllib.parse import parse_qs

import httpx
import pytest
import respx

from backend.api.auth import GENERATE_QRCODE_URL, POLL_QRCODE_URL
from backend.api.comment import DELETE_COMMENT_URL, REPLY_HISTORY_URL
from backend.api.dynamic import DELETE_DYNAMIC_URL, DYNAMICS_URL
from backend.api.favorite import BATCH_DELETE_URL, FOLDERS_URL, RESOURCE_IDS_URL
from backend.api.history import CLEAR_HISTORY_URL
from backend.api.relation import BATCH_MODIFY_URL, FOLLOWINGS_URL

pytestmark = pytest.mark.asyncio


def parse_form(request: httpx.Request) -> dict[str, list[str]]:
    return parse_qs(request.content.decode())


async def test_get_qrcode(async_client: httpx.AsyncClient) -> None:
    with respx.mock(assert_all_called=True, assert_all_mocked=False) as router:
        router.get(GENERATE_QRCODE_URL).mock(
            return_value=httpx.Response(
                200,
                json={"code": 0, "data": {"url": "https://qrcode", "qrcode_key": "key"}},
            )
        )
        response = await async_client.get("/api/qrcode")

    assert response.status_code == 200
    payload = response.json()
    assert payload["qrcode_key"] == "key"
    image_bytes = base64.b64decode(payload["image"])
    assert image_bytes


async def test_poll_qrcode(async_client: httpx.AsyncClient) -> None:
    with respx.mock(assert_all_called=True, assert_all_mocked=False) as router:
        router.get(POLL_QRCODE_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"status": 1}})
        )
        response = await async_client.get("/api/qrcode/poll/test-key")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["status"] == 1


async def test_clean_followings(async_client: httpx.AsyncClient, auth_headers: dict[str, str]) -> None:
    followings_responses = [
        httpx.Response(200, json={"code": 0, "data": {"list": [{"mid": 1}, {"mid": 2}]}}),
        httpx.Response(200, json={"code": 0, "data": {"list": []}}),
    ]
    with respx.mock(assert_all_called=True, assert_all_mocked=False) as router:
        router.get(FOLLOWINGS_URL).mock(side_effect=followings_responses)
        batch_route = router.post(BATCH_MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        response = await async_client.post("/api/clean/followings", json={"mid": 123}, headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["count"] == 2
    form = parse_form(batch_route.calls[0].request)
    assert form["fids"] == ["1,2"]


async def test_clean_favorites(async_client: httpx.AsyncClient, auth_headers: dict[str, str]) -> None:
    with respx.mock(assert_all_called=True, assert_all_mocked=False) as router:
        router.get(FOLDERS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"list": [{"id": 10}]}})
        )
        router.get(RESOURCE_IDS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ids": [1, 2]}})
        )
        delete_route = router.post(BATCH_DELETE_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"success": True}})
        )
        response = await async_client.post("/api/clean/favorites", json={"mid": 456}, headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["count"] == 2
    form = parse_form(delete_route.calls[0].request)
    assert form["media_id"] == ["10"]


async def test_clean_dynamics(async_client: httpx.AsyncClient, auth_headers: dict[str, str]) -> None:
    with respx.mock(assert_all_called=True, assert_all_mocked=False) as router:
        router.get(DYNAMICS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"items": [{"id": 111}, {"id": 222}], "has_more": False},
                },
            )
        )
        delete_route = router.post(DELETE_DYNAMIC_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        response = await async_client.post("/api/clean/dynamics", json={"mid": 999}, headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["count"] == 2
    assert len(delete_route.calls) == 2


async def test_clean_history(async_client: httpx.AsyncClient, auth_headers: dict[str, str]) -> None:
    with respx.mock(assert_all_called=True, assert_all_mocked=False) as router:
        router.post(CLEAR_HISTORY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        response = await async_client.post("/api/clean/history", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["count"] == 1  # 返回 1 表示操作已执行


async def test_clean_all(async_client: httpx.AsyncClient, auth_headers: dict[str, str]) -> None:
    followings_responses = [
        httpx.Response(200, json={"code": 0, "data": {"list": [{"mid": 1}]}}),
        httpx.Response(200, json={"code": 0, "data": {"list": []}}),
    ]
    dynamics_responses = [
        httpx.Response(
            200,
            json={"code": 0, "data": {"items": [{"id_str": "333"}], "has_more": False}},
        )
    ]
    with respx.mock(assert_all_called=True, assert_all_mocked=False) as router:
        router.get(FOLLOWINGS_URL).mock(side_effect=followings_responses)
        router.post(BATCH_MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        router.get(FOLDERS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"list": [{"media_id": 20}]}})
        )
        router.get(RESOURCE_IDS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ids": [10]}})
        )
        router.post(BATCH_DELETE_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"success": True}})
        )
        router.get(DYNAMICS_URL).mock(side_effect=dynamics_responses)
        router.post(DELETE_DYNAMIC_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        router.post(CLEAR_HISTORY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        router.get(REPLY_HISTORY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"items": [], "cursor": {"is_end": True}}})
        )
        response = await async_client.post("/api/clean/all", json={"mid": 100}, headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["counts"] == {
        "followings": 1,
        "favorites": 1,
        "dynamics": 1,
        "comments": 0,
        "history": 1,
    }
    assert payload["total"] == 4


async def test_auth_required(async_client: httpx.AsyncClient) -> None:
    response = await async_client.post("/api/clean/followings", json={"mid": 123})
    assert response.status_code == 401
    payload = response.json()
    assert payload["error"] == "Missing SESSDATA or bili_jct"
