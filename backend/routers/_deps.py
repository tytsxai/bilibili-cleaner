from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, Header, HTTPException, status

from backend.api import BiliApiClient
from backend.services.tasks import owner_key
from backend.settings import settings

DEFAULT_API_QPS = settings.api_qps


def get_auth_headers(
    sessdata: str | None = Header(None, alias="SESSDATA"),
    bili_jct: str | None = Header(None, alias="bili_jct"),
) -> tuple[str, str]:
    if not sessdata or not bili_jct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing SESSDATA or bili_jct",
        )
    return sessdata, bili_jct


def build_client(
    auth: tuple[str, str] | None = None, *, qps: float | None = DEFAULT_API_QPS
) -> BiliApiClient:
    """Single place where an outbound client is configured.

    Every caller must go through here. Constructing ``BiliApiClient`` inline
    silently skips the configured timeout and retry policy — which used to be
    the case for exactly the long-running background cleans that need it most.
    """
    sessdata, bili_jct = auth if auth else (None, None)
    return BiliApiClient(
        sessdata=sessdata,
        bili_jct=bili_jct,
        qps=qps,
        timeout=settings.http_timeout,
        max_retries=settings.max_retries,
        retry_base_delay=settings.retry_base_delay,
    )


@asynccontextmanager
async def authed_client(
    auth: tuple[str, str], qps: float | None = DEFAULT_API_QPS
) -> AsyncIterator[BiliApiClient]:
    async with build_client(auth, qps=qps) as client:
        yield client


@asynccontextmanager
async def anon_client(qps: float | None = DEFAULT_API_QPS) -> AsyncIterator[BiliApiClient]:
    """For the QR-code login flow, which has no credentials yet."""
    async with build_client(None, qps=qps) as client:
        yield client


def task_owner(auth: tuple[str, str]) -> str:
    """Owner id for tasks created by this caller. See ``owner_key``."""
    return owner_key(auth[0])


AuthDep = Depends(get_auth_headers)
