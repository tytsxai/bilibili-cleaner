from __future__ import annotations

import httpx
import pytest
import respx

from backend.api.client import BiliApiClient
from backend.api.relation import FOLLOWINGS_URL, MODIFY_URL
from backend.api.user import ACC_INFO_URL, ARC_SEARCH_URL, RELATION_STAT_URL
from backend.api.wbi import NAV_URL
from backend.services.following import FollowingService

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


def _followings_page(items: list[dict], total: int = 100):
    return httpx.Response(200, json={"code": 0, "data": {"list": items, "total": total}})


async def test_iter_all_pages_through(client: BiliApiClient) -> None:
    service = FollowingService(client)
    with respx.mock() as router:
        page1 = [{"mid": i, "uname": f"u{i}"} for i in range(50)]
        page2 = [{"mid": 50, "uname": "u50"}]
        route = router.get(FOLLOWINGS_URL).mock(
            side_effect=[_followings_page(page1), _followings_page(page2)]
        )
        result = [item async for item in service.iter_all(123, page_size=50)]
        assert len(result) == 51
        assert route.call_count == 2


async def test_iter_all_stops_on_empty(client: BiliApiClient) -> None:
    service = FollowingService(client)
    with respx.mock() as router:
        router.get(FOLLOWINGS_URL).mock(return_value=_followings_page([]))
        result = [item async for item in service.iter_all(123)]
        assert result == []


async def test_get_detail_combines_endpoints(client: BiliApiClient) -> None:
    service = FollowingService(client)
    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get(ACC_INFO_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"mid": 7, "name": "alice", "sign": "hi"}}
            )
        )
        router.get(RELATION_STAT_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"mid": 7, "follower": 1234}}
            )
        )
        router.get(ARC_SEARCH_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "list": {"vlist": [{"aid": 1, "bvid": "BV1", "pubdate": 1700000000}]},
                        "page": {"pn": 1, "ps": 1, "count": 42},
                    },
                },
            )
        )
        detail = await service.get_detail(7)
        assert detail["mid"] == 7
        assert detail["info"]["name"] == "alice"
        assert detail["stat"]["follower"] == 1234
        assert detail["latest_video"]["bvid"] == "BV1"
        assert detail["video_count"] == 42


async def test_get_detail_records_partial_failures(client: BiliApiClient) -> None:
    service = FollowingService(client)
    with respx.mock() as router:
        router.get(NAV_URL).mock(return_value=httpx.Response(200, json=NAV_PAYLOAD))
        router.get(ACC_INFO_URL).mock(
            return_value=httpx.Response(200, json={"code": -404, "message": "no user"})
        )
        router.get(RELATION_STAT_URL).mock(
            return_value=httpx.Response(
                200, json={"code": 0, "data": {"follower": 5}}
            )
        )
        router.get(ARC_SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"code": -404, "message": "no videos"})
        )
        detail = await service.get_detail(99)
        assert detail["info"].get("_error")
        assert detail["info"]["_code"] == -404
        assert detail["stat"]["follower"] == 5
        assert detail["latest_video"].get("_error")


async def test_unfollow_many_records_errors(client: BiliApiClient) -> None:
    service = FollowingService(client)
    with respx.mock() as router:
        router.post(MODIFY_URL).mock(
            side_effect=[
                httpx.Response(200, json={"code": 0, "data": {}}),
                httpx.Response(200, json={"code": -101, "message": "fail"}),
                httpx.Response(200, json={"code": 0, "data": {}}),
            ]
        )
        progress: list[tuple[int, bool]] = []
        result = await service.unfollow_many(
            [1, 2, 3], on_item=lambda mid, ok, err: progress.append((mid, ok))
        )
        assert result["ok"] == 2
        assert len(result["errors"]) == 1
        assert progress == [(1, True), (2, False), (3, True)]


async def test_clear_all_loops_until_empty(client: BiliApiClient) -> None:
    service = FollowingService(client)
    with respx.mock() as router:
        page = [{"mid": 1}, {"mid": 2}]
        router.get(FOLLOWINGS_URL).mock(
            side_effect=[
                _followings_page(page),
                _followings_page([]),
            ]
        )
        router.post(MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": 0, "data": {}})
        )
        result = await service.clear_all(999)
        assert result["ok"] == 2
        assert result["errors"] == []


async def test_clear_all_stops_when_page_makes_no_progress(client: BiliApiClient) -> None:
    client._max_retries = 0
    service = FollowingService(client)
    with respx.mock() as router:
        followings_route = router.get(FOLLOWINGS_URL).mock(
            return_value=_followings_page([{"mid": 1}, {"mid": 2}])
        )
        modify_route = router.post(MODIFY_URL).mock(
            return_value=httpx.Response(200, json={"code": -352, "message": "risk"})
        )
        progress: list[tuple[int, bool]] = []
        result = await service.clear_all(
            999,
            on_item=lambda mid, ok, err: progress.append((mid, ok)),
        )

        assert result["ok"] == 0
        assert result["stopped_reason"] == "no_progress"
        assert len(result["errors"]) == 2
        assert progress == [(1, False), (2, False)]
        assert followings_route.call_count == 1
        assert modify_route.call_count == 2
