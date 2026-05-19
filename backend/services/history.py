from __future__ import annotations

from typing import Any

from backend.api import HistoryApi
from backend.api.client import BiliApiClient


class HistoryService:
    def __init__(self, client: BiliApiClient) -> None:
        self._api = HistoryApi(client)

    async def list_page(
        self,
        *,
        max_id: int = 0,
        business: str = "",
        view_at: int = 0,
        page_size: int = 20,
        type_: str = "all",
    ) -> dict[str, Any]:
        return await self._api.list_history(
            max_id=max_id,
            business=business,
            view_at=view_at,
            ps=page_size,
            type_=type_,
        )

    async def delete(self, kid: str) -> dict[str, Any]:
        return await self._api.delete_history(kid)

    async def clear(self) -> dict[str, Any]:
        return await self._api.clear_history()
