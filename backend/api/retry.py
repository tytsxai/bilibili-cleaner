from __future__ import annotations

import asyncio
import random

from .client import BiliApiError

RISK_CONTROL_CODES: frozenset[int] = frozenset({-352, -799, -509})
RISK_CONTROL_HTTP_STATUS: frozenset[int] = frozenset({412, 429})


def is_risk_control_error(exc: BiliApiError) -> bool:
    """Return True if the error matches B 站 risk-control / rate-limit signals."""
    if exc.code is not None and exc.code in RISK_CONTROL_CODES:
        return True
    if exc.status_code is not None and exc.status_code in RISK_CONTROL_HTTP_STATUS:
        return True
    return False


def compute_backoff(attempt: int, base: float, cap: float = 30.0) -> float:
    """Exponential backoff with full jitter, capped at ``cap`` seconds."""
    expo = min(cap, base * (2 ** attempt))
    return random.uniform(base, base + expo)


async def sleep_backoff(attempt: int, base: float) -> None:
    await asyncio.sleep(compute_backoff(attempt, base))
