from __future__ import annotations

import asyncio
import time


class AsyncTokenBucket:
    """Async token bucket rate limiter.

    A single bucket shared by all callers. ``acquire()`` blocks until a token
    is available, then consumes it. Default ``burst`` of 1 yields strict
    spacing of ``1/qps`` seconds between successive calls.
    """

    def __init__(self, qps: float, burst: int = 1) -> None:
        if qps <= 0:
            raise ValueError("qps must be positive")
        if burst < 1:
            raise ValueError("burst must be >= 1")
        self._qps = float(qps)
        self._burst = burst
        self._tokens = float(burst)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._tokens = min(float(self._burst), self._tokens + elapsed * self._qps)
            self._last = now
            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self._qps
                await asyncio.sleep(wait)
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(float(self._burst), self._tokens + elapsed * self._qps)
                self._last = now
            self._tokens -= 1.0
