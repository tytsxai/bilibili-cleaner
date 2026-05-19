from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, Header, HTTPException, status

from backend.api import BiliApiClient

DEFAULT_API_QPS = 1.5


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


@asynccontextmanager
async def authed_client(
    auth: tuple[str, str], qps: float | None = DEFAULT_API_QPS
) -> AsyncIterator[BiliApiClient]:
    sessdata, bili_jct = auth
    async with BiliApiClient(
        sessdata=sessdata, bili_jct=bili_jct, qps=qps
    ) as client:
        yield client


AuthDep = Depends(get_auth_headers)
