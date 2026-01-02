from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest
import respx

from backend.api.favorite import BATCH_DELETE_URL, FOLDERS_URL, RESOURCE_IDS_URL
from backend.api.dynamic import DELETE_DYNAMIC_URL, DYNAMICS_URL
from backend.api.history import CLEAR_HISTORY_URL
from backend.api.relation import BATCH_MODIFY_URL, FOLLOWINGS_URL
from backend.services.cleaner import CleanerService
from backend.api.client import BiliApiClient

pytestmark = pytest.mark.asyncio


def parse_form(request: httpx.Request) -> dict[str, list[str]]:
    return parse_qs(request.content.decode())


async def test_clear_all_followings(bili_client: BiliApiClient) -> None:
    service = CleanerService(bili_client)
    followings_responses = [
        httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"list": [{"mid": 1}, {"mid": "2"}, {"mid": None}]},
            },
        ),
        httpx.Response(200, json={"code": 0, "data": {"list": []}}),
    ]
    with respx.mock(assert_all_called=True) as router:
        followings_route = router.get(FOLLOWINGS_URL).mock(side_effect=followings_responses)
        batch_route = router.post(BATCH_MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        result = await service.clear_all_followings(123)

    assert result.count == 2
    assert len(followings_route.calls) == 2
    assert len(batch_route.calls) == 1
    form = parse_form(batch_route.calls[0].request)
    assert form["fids"] == ["1,2"]
    assert form["act"] == ["2"]


async def test_clear_all_favorites(bili_client: BiliApiClient) -> None:
    service = CleanerService(bili_client)
    folders_payload = {
        "code": 0,
        "data": {
            "list": [
                {"id": "100"},
                {"id": None},
                "invalid",
            ]
        },
    }
    with respx.mock(assert_all_called=True) as router:
        router.get(FOLDERS_URL).mock(return_value=httpx.Response(200, json=folders_payload))
        ids_route = router.get(RESOURCE_IDS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ids": [1, "2", None]}})
        )
        delete_route = router.post(BATCH_DELETE_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"success": True}})
        )
        result = await service.clear_all_favorites(123)

    assert result.count == 2
    assert len(ids_route.calls) == 1
    form = parse_form(delete_route.calls[0].request)
    assert form["media_id"] == ["100"]
    assert form["resources"] == ["1:2,2:2"]


async def test_clear_all_dynamics(bili_client: BiliApiClient) -> None:
    service = CleanerService(bili_client)
    dynamic_responses = [
        httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "items": [{"id_str": "11"}, {"id": 22}, {"bad": "x"}, "skip"],
                    "has_more": True,
                    "offset": "next",
                },
            },
        ),
        httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"items": [{"dynamic_id": "33"}], "has_more": False},
            },
        ),
    ]
    with respx.mock(assert_all_called=True) as router:
        dynamics_route = router.get(DYNAMICS_URL).mock(side_effect=dynamic_responses)
        delete_route = router.post(DELETE_DYNAMIC_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        result = await service.clear_all_dynamics(456)

    assert result.count == 3
    assert len(dynamics_route.calls) == 2
    assert len(delete_route.calls) == 3


async def test_clear_history(bili_client: BiliApiClient) -> None:
    service = CleanerService(bili_client)
    with respx.mock(assert_all_called=True) as router:
        router.post(CLEAR_HISTORY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ok": True}})
        )
        result = await service.clear_history()

    assert result.count == 0
