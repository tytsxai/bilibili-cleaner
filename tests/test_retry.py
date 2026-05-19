from __future__ import annotations

import httpx
import pytest
import respx

from backend.api.client import BiliApiClient, BiliApiError
from backend.api.retry import (
    compute_backoff,
    is_risk_control_error,
)

pytestmark = pytest.mark.asyncio

URL = "https://api.bilibili.com/test"


async def test_is_risk_control_codes() -> None:
    assert is_risk_control_error(BiliApiError("x", code=-352))
    assert is_risk_control_error(BiliApiError("x", code=-799))
    assert is_risk_control_error(BiliApiError("x", code=-509))
    assert not is_risk_control_error(BiliApiError("x", code=-101))
    assert not is_risk_control_error(BiliApiError("x", code=0))
    assert not is_risk_control_error(BiliApiError("x"))


async def test_is_risk_control_http_status() -> None:
    assert is_risk_control_error(BiliApiError("x", status_code=412))
    assert is_risk_control_error(BiliApiError("x", status_code=429))
    assert not is_risk_control_error(BiliApiError("x", status_code=500))
    assert not is_risk_control_error(BiliApiError("x", status_code=401))


async def test_compute_backoff_bounded() -> None:
    for attempt in range(0, 5):
        delay = compute_backoff(attempt, base=0.01, cap=1.0)
        assert delay >= 0.01
        assert delay <= 0.01 + 1.0 + 0.001


async def test_retries_on_risk_control_then_succeeds() -> None:
    client = BiliApiClient(max_retries=3, retry_base_delay=0.001)
    try:
        with respx.mock(assert_all_called=True) as router:
            route = router.get(URL).mock(
                side_effect=[
                    httpx.Response(200, json={"code": -352, "message": "risk"}),
                    httpx.Response(200, json={"code": -352, "message": "risk"}),
                    httpx.Response(200, json={"code": 0, "data": {"ok": True}}),
                ]
            )
            data = await client.get(URL)
            assert data["data"]["ok"] is True
            assert route.call_count == 3
    finally:
        await client.close()


async def test_retries_on_http_412() -> None:
    client = BiliApiClient(max_retries=2, retry_base_delay=0.001)
    try:
        with respx.mock(assert_all_called=True) as router:
            route = router.get(URL).mock(
                side_effect=[
                    httpx.Response(412, text="rate limit"),
                    httpx.Response(200, json={"code": 0, "data": {"ok": True}}),
                ]
            )
            data = await client.get(URL)
            assert data["data"]["ok"] is True
            assert route.call_count == 2
    finally:
        await client.close()


async def test_does_not_retry_other_errors() -> None:
    client = BiliApiClient(max_retries=3, retry_base_delay=0.001)
    try:
        with respx.mock() as router:
            route = router.get(URL).mock(
                return_value=httpx.Response(200, json={"code": -101, "message": "unauthorized"})
            )
            with pytest.raises(BiliApiError) as exc:
                await client.get(URL)
            assert exc.value.code == -101
            assert route.call_count == 1
    finally:
        await client.close()


async def test_exhausts_retries_then_raises() -> None:
    client = BiliApiClient(max_retries=2, retry_base_delay=0.001)
    try:
        with respx.mock() as router:
            route = router.get(URL).mock(
                return_value=httpx.Response(200, json={"code": -352, "message": "risk"})
            )
            with pytest.raises(BiliApiError) as exc:
                await client.get(URL)
            assert exc.value.code == -352
            assert route.call_count == 3
    finally:
        await client.close()


async def test_zero_retries_no_loop() -> None:
    client = BiliApiClient(max_retries=0, retry_base_delay=0.001)
    try:
        with respx.mock() as router:
            route = router.get(URL).mock(
                return_value=httpx.Response(200, json={"code": -352, "message": "risk"})
            )
            with pytest.raises(BiliApiError):
                await client.get(URL)
            assert route.call_count == 1
    finally:
        await client.close()
