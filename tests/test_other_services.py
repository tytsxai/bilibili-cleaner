from __future__ import annotations

import httpx
import pytest
import respx

from backend.api.client import BiliApiClient
from backend.api.dynamic import DELETE_DYNAMIC_URL, DYNAMICS_URL
from backend.api.favorite import BATCH_DELETE_URL, FOLDERS_URL, RESOURCE_IDS_URL, RESOURCE_LIST_URL
from backend.api.relation_tag import COPY_USERS_URL, CREATE_TAG_URL, LIST_TAGS_URL, MOVE_USERS_URL
from backend.api.wbi import NAV_URL
from backend.services.dynamic import DynamicService
from backend.services.favorite import FavoriteService
from backend.services.tag import TagService

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
    c = BiliApiClient(sessdata="sess", bili_jct="csrf")
    yield c
    await c.close()


async def test_dynamic_iter_all_pages_through_offset(client: BiliApiClient) -> None:
    service = DynamicService(client)
    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get(DYNAMICS_URL).mock(
            side_effect=[
                httpx.Response(
                    200,
                    json={
                        "code": 0,
                        "data": {
                            "items": [{"id_str": "1"}, {"id_str": "2"}],
                            "has_more": True,
                            "offset": "cursor1",
                        },
                    },
                ),
                httpx.Response(
                    200,
                    json={
                        "code": 0,
                        "data": {"items": [{"id_str": "3"}], "has_more": False},
                    },
                ),
            ]
        )
        collected = [item async for item in service.iter_all(42)]
        assert [i["id_str"] for i in collected] == ["1", "2", "3"]


async def test_dynamic_delete_many_handles_invalid(client: BiliApiClient) -> None:
    service = DynamicService(client)
    with respx.mock() as router:
        router.post(DELETE_DYNAMIC_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        result = await service.delete_many(["100", "not-a-number", "200"])
        assert result["ok"] == 2
        assert len(result["errors"]) == 1
        assert result["errors"][0]["id"] == "not-a-number"


async def test_dynamic_clear_all_records_errors(client: BiliApiClient) -> None:
    service = DynamicService(client)
    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get(DYNAMICS_URL).mock(
            side_effect=[
                httpx.Response(
                    200,
                    json={
                        "code": 0,
                        "data": {
                            "items": [{"id_str": "1"}, {"id_str": "2"}],
                            "has_more": False,
                        },
                    },
                ),
            ]
        )
        router.post(DELETE_DYNAMIC_URL).mock(
            side_effect=[
                httpx.Response(200, json={"code": 0, "data": {}}),
                httpx.Response(200, json={"code": -500, "message": "fail"}),
            ]
        )
        result = await service.clear_all(42)
        assert result["ok"] == 1
        assert len(result["errors"]) == 1


async def test_favorite_delete_resources_mixed_inputs(client: BiliApiClient) -> None:
    service = FavoriteService(client)
    with respx.mock() as router:
        router.post(BATCH_DELETE_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        result = await service.delete_resources(
            9, [1, "3:2", {"id": 5, "type": 2}, {"type": 2}]
        )
        assert result["ok"] == 3
        assert result["total"] == 3


async def test_favorite_iter_items_pages_until_short(client: BiliApiClient) -> None:
    service = FavoriteService(client)
    with respx.mock() as router:
        router.get(RESOURCE_LIST_URL).mock(
            side_effect=[
                httpx.Response(
                    200,
                    json={
                        "code": 0,
                        "data": {"medias": [{"id": i} for i in range(20)]},
                    },
                ),
                httpx.Response(
                    200,
                    json={"code": 0, "data": {"medias": [{"id": 99}]}},
                ),
            ]
        )
        items = [it async for it in service.iter_items(9, page_size=20)]
        assert len(items) == 21


async def test_favorite_clear_all_records_per_batch_errors(client: BiliApiClient) -> None:
    service = FavoriteService(client)
    with respx.mock() as router:
        router.get(FOLDERS_URL).mock(
            return_value=httpx.Response(
                200,
                json={"code": 0, "data": {"list": [{"id": 9, "title": "x"}]}},
            )
        )
        router.get(RESOURCE_IDS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"ids": [1, 2]}})
        )
        router.post(BATCH_DELETE_URL).mock(
            return_value=httpx.Response(200, json={"code": -500, "message": "fail"})
        )
        result = await service.clear_all(123)
        assert result["ok"] == 0
        assert len(result["errors"]) == 1


async def test_tag_users_finds_existing_by_name(client: BiliApiClient) -> None:
    service = TagService(client)
    with respx.mock() as router:
        router.get(LIST_TAGS_URL).mock(
            return_value=httpx.Response(
                200,
                json={"code": 0, "data": [{"tagid": 5, "name": "review"}]},
            )
        )
        router.post(COPY_USERS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        result = await service.tag_users([1, 2], tag_name="review")
        assert result["tagid"] == 5
        assert result["count"] == 2


async def test_tag_users_creates_when_missing(client: BiliApiClient) -> None:
    service = TagService(client)
    with respx.mock() as router:
        router.get(LIST_TAGS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": []})
        )
        router.post(CREATE_TAG_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"tagid": 77}})
        )
        router.post(MOVE_USERS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        result = await service.tag_users([1, 2], tag_name="new-tag", replace=True)
        assert result["tagid"] == 77


async def test_tag_users_requires_identifier() -> None:
    client = BiliApiClient()
    try:
        service = TagService(client)
        with pytest.raises(ValueError):
            await service.tag_users([1])
    finally:
        await client.close()
