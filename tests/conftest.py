from __future__ import annotations

import httpx
import pytest

from backend.main import app
from backend.api.client import BiliApiClient


@pytest.fixture
async def async_client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def bili_client() -> BiliApiClient:
    client = BiliApiClient(sessdata="sessdata", bili_jct="csrf-token")
    yield client
    await client.close()


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"SESSDATA": "sessdata", "bili_jct": "csrf-token"}
