from __future__ import annotations

from typing import Any, Sequence

from .client import BiliApiClient

FOLLOWINGS_URL = "https://api.bilibili.com/x/relation/followings"
BATCH_MODIFY_URL = "https://api.bilibili.com/x/relation/batch/modify"


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

    async def batch_unfollow(self, mids: Sequence[int]) -> dict[str, Any]:
        if len(mids) > 50:
            raise ValueError("batch_unfollow supports up to 50 mids per request")
        fids = ",".join(str(mid) for mid in mids)
        payload = await self._client.post(
            BATCH_MODIFY_URL,
            data={"fids": fids, "act": 2},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}
