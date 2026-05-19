from __future__ import annotations

from urllib.parse import parse_qs

import httpx
import pytest
import respx

from backend.api.client import BiliApiClient
from backend.api.relation_tag import (
    COPY_USERS_URL,
    CREATE_TAG_URL,
    DELETE_TAG_URL,
    LIST_TAGS_URL,
    MOVE_USERS_URL,
    RelationTagApi,
    TAG_USERS_URL,
    UPDATE_TAG_URL,
)

pytestmark = pytest.mark.asyncio
CSRF = "csrf-token"


@pytest.fixture
async def client() -> BiliApiClient:
    c = BiliApiClient(sessdata="sess", bili_jct=CSRF)
    yield c
    await c.close()


def _form(req: httpx.Request) -> dict[str, list[str]]:
    return parse_qs(req.content.decode())


async def test_list_tags(client: BiliApiClient) -> None:
    api = RelationTagApi(client)
    with respx.mock(assert_all_called=True) as router:
        router.get(LIST_TAGS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": [
                        {"tagid": 0, "name": "默认", "count": 100},
                        {"tagid": 12, "name": "review", "count": 0},
                    ],
                },
            )
        )
        tags = await api.list_tags()
        assert len(tags) == 2
        assert tags[1]["name"] == "review"


async def test_create_tag(client: BiliApiClient) -> None:
    api = RelationTagApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.post(CREATE_TAG_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {"tagid": 12}})
        )
        data = await api.create_tag("review")
        assert data["tagid"] == 12
        form = _form(route.calls[0].request)
        assert form["tag"] == ["review"]
        assert form["csrf"] == [CSRF]


async def test_delete_tag(client: BiliApiClient) -> None:
    api = RelationTagApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.post(DELETE_TAG_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        await api.delete_tag(12)
        form = _form(route.calls[0].request)
        assert form["tagid"] == ["12"]


async def test_rename_tag(client: BiliApiClient) -> None:
    api = RelationTagApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.post(UPDATE_TAG_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        await api.rename_tag(12, "review-new")
        form = _form(route.calls[0].request)
        assert form["tagid"] == ["12"]
        assert form["name"] == ["review-new"]


async def test_copy_users_to_tag(client: BiliApiClient) -> None:
    api = RelationTagApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.post(COPY_USERS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        await api.copy_users_to_tag([1, 2, 3], [12])
        form = _form(route.calls[0].request)
        assert form["fids"] == ["1,2,3"]
        assert form["tagids"] == ["12"]


async def test_move_users_to_tag(client: BiliApiClient) -> None:
    api = RelationTagApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.post(MOVE_USERS_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        await api.move_users_to_tag([5], [12, 13])
        form = _form(route.calls[0].request)
        assert form["fids"] == ["5"]
        assert form["tagids"] == ["12,13"]


async def test_list_tag_users(client: BiliApiClient) -> None:
    api = RelationTagApi(client)
    with respx.mock(assert_all_called=True) as router:
        route = router.get(TAG_USERS_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": [{"mid": 1}, {"mid": 2}]}
            )
        )
        users = await api.list_tag_users(12, pn=1, ps=20)
        assert len(users) == 2
        params = route.calls[0].request.url.params
        assert params["tagid"] == "12"
