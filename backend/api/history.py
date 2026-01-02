from __future__ import annotations

from typing import Any

from .client import BiliApiClient

CLEAR_HISTORY_URL = "https://api.bilibili.com/x/v2/history/clear"


class HistoryApi:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def clear_history(self) -> dict[str, Any]:
        payload = await self._client.post(CLEAR_HISTORY_URL, data={}, include_csrf=True)
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}
