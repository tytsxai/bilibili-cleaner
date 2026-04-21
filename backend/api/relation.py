from __future__ import annotations

from typing import Any

from .client import BiliApiClient

FOLLOWINGS_URL = "https://api.bilibili.com/x/relation/followings"
MODIFY_URL = "https://api.bilibili.com/x/relation/modify"


class RelationApi:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def get_followings(self, mid: int, pn: int = 1, ps: int = 50) -> dict[str, Any]:
        payload = await self._client.get(
            FOLLOWINGS_URL,
            params={"vmid": mid, "pn": pn, "ps": ps},
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def unfollow(self, mid: int) -> dict[str, Any]:
        payload = await self._client.post(
            MODIFY_URL,
            data={"fid": mid, "act": 2, "re_src": 11},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}
