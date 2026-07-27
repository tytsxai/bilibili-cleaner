from __future__ import annotations

from dataclasses import replace

import httpx
import pytest

from backend import audit
from backend.api import wbi
from backend.api.client import BiliApiClient
from backend.main import app
from backend.services import tasks as tasks_module


@pytest.fixture(autouse=True)
def isolate_process_state(tmp_path, monkeypatch):
    """Reset process-wide caches between tests.

    The WBI keys and the task registry are deliberately global at runtime, so
    without this a test would inherit keys fetched by an earlier one (and its
    mocked ``/nav`` route would never be called).
    """
    wbi.invalidate_cache()
    tasks_module.reset_for_tests()
    # Settings is frozen, so swap the module-level binding instead of mutating.
    monkeypatch.setattr(
        audit,
        "settings",
        replace(
            audit.settings,
            audit_log_enabled=True,
            audit_log_path=str(tmp_path / "audit.jsonl"),
        ),
    )
    audit.reset_for_tests()
    yield
    wbi.invalidate_cache()
    tasks_module.reset_for_tests()
    audit.reset_for_tests()


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
