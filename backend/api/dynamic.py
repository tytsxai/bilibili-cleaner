from __future__ import annotations

from typing import Any

from .client import BiliApiClient

DYNAMICS_URL = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space"
DELETE_DYNAMIC_URL = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/rm_dynamic"


class DynamicApi:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def get_dynamics(self, mid: int, offset: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"host_mid": mid}
        if offset:
            params["offset"] = offset
        payload = await self._client.get(DYNAMICS_URL, params=params)
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def delete_dynamic(self, dynamic_id: int) -> dict[str, Any]:
        payload = await self._client.post(
            DELETE_DYNAMIC_URL,
            data={"dynamic_id": dynamic_id},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}
