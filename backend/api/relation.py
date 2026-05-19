from __future__ import annotations

from typing import Any

from .client import BiliApiClient

FOLLOWINGS_URL = "https://api.bilibili.com/x/relation/followings"
MODIFY_URL = "https://api.bilibili.com/x/relation/modify"
RELATION_URL = "https://api.bilibili.com/x/relation"


class RelationApi:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def get_followings(
        self,
        mid: int,
        pn: int = 1,
        ps: int = 50,
        order: str = "desc",
        order_type: str = "attention",
    ) -> dict[str, Any]:
        payload = await self._client.get(
            FOLLOWINGS_URL,
            params={
                "vmid": mid,
                "pn": pn,
                "ps": ps,
                "order": order,
                "order_type": order_type,
            },
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def unfollow(self, mid: int) -> dict[str, Any]:
        return await self._modify(mid, act=2)

    async def follow(self, mid: int) -> dict[str, Any]:
        return await self._modify(mid, act=1)

    async def _modify(self, mid: int, *, act: int) -> dict[str, Any]:
        payload = await self._client.post(
            MODIFY_URL,
            data={"fid": mid, "act": act, "re_src": 11},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def get_following_state(self, mid: int) -> dict[str, Any]:
        """Returns ``{relation: {status, ...}, be_relation: {...}}`` for ``mid``.

        ``relation.status`` of 2/6 means you currently follow this user.
        """
        payload = await self._client.get(RELATION_URL, params={"fid": mid, "jsonp": "jsonp"})
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}
