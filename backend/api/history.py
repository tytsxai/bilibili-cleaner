from __future__ import annotations

from typing import Any

from .client import BiliApiClient

CLEAR_HISTORY_URL = "https://api.bilibili.com/x/v2/history/clear"
HISTORY_CURSOR_URL = "https://api.bilibili.com/x/web-interface/history/cursor"
DELETE_HISTORY_URL = "https://api.bilibili.com/x/v2/history/delete"


class HistoryApi:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def list_history(
        self,
        *,
        max_id: int = 0,
        business: str = "",
        view_at: int = 0,
        ps: int = 20,
        type_: str = "all",
    ) -> dict[str, Any]:
        """List recent watch history. Returned ``data`` has ``cursor`` (for
        next page) and ``list`` of items."""
        params: dict[str, Any] = {
            "max": max_id,
            "business": business,
            "view_at": view_at,
            "ps": ps,
            "type": type_,
        }
        payload = await self._client.get(HISTORY_CURSOR_URL, params=params)
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def delete_history(self, kid: str) -> dict[str, Any]:
        """Delete a single history entry.

        ``kid`` format: ``archive_<aid>``, ``pgc_<epid>``, etc.
        """
        payload = await self._client.post(
            DELETE_HISTORY_URL,
            data={"kid": kid},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def clear_history(self) -> dict[str, Any]:
        payload = await self._client.post(CLEAR_HISTORY_URL, data={}, include_csrf=True)
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}
