from __future__ import annotations

import asyncio
import time

import pytest

from backend.api.ratelimit import AsyncTokenBucket

pytestmark = pytest.mark.asyncio


async def test_first_token_is_immediate() -> None:
    bucket = AsyncTokenBucket(qps=10, burst=1)
    start = time.monotonic()
    await bucket.acquire()
    assert time.monotonic() - start < 0.05


async def test_spacing_matches_qps() -> None:
    qps = 20.0
    bucket = AsyncTokenBucket(qps=qps, burst=1)
    n = 5
    start = time.monotonic()
    for _ in range(n):
        await bucket.acquire()
    elapsed = time.monotonic() - start
    expected = (n - 1) / qps
    assert elapsed >= expected * 0.9, f"elapsed={elapsed:.3f} expected>={expected:.3f}"


async def test_burst_allows_concurrent_acquires() -> None:
    bucket = AsyncTokenBucket(qps=10, burst=3)
    start = time.monotonic()
    await asyncio.gather(bucket.acquire(), bucket.acquire(), bucket.acquire())
    assert time.monotonic() - start < 0.1


async def test_concurrent_acquires_are_serialized() -> None:
    qps = 20.0
    bucket = AsyncTokenBucket(qps=qps, burst=1)
    start = time.monotonic()
    await asyncio.gather(*(bucket.acquire() for _ in range(4)))
    elapsed = time.monotonic() - start
    expected = 3 / qps
    assert elapsed >= expected * 0.9, f"elapsed={elapsed:.3f} expected>={expected:.3f}"


async def test_rejects_invalid_args() -> None:
    with pytest.raises(ValueError):
        AsyncTokenBucket(qps=0)
    with pytest.raises(ValueError):
        AsyncTokenBucket(qps=-1)
    with pytest.raises(ValueError):
        AsyncTokenBucket(qps=1, burst=0)
