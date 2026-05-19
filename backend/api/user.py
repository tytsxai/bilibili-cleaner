from __future__ import annotations

from typing import Any

from .client import BiliApiClient
from .wbi import signed_get

ACC_INFO_URL = "https://api.bilibili.com/x/space/wbi/acc/info"
ARC_SEARCH_URL = "https://api.bilibili.com/x/space/wbi/arc/search"
RELATION_STAT_URL = "https://api.bilibili.com/x/relation/stat"


class UserApi:
    """Wrappers for public UP profile endpoints used by quality filters."""

    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def get_info(self, mid: int) -> dict[str, Any]:
        params = {"mid": mid, "token": "", "platform": "web", "web_location": "1550101"}
        headers = {"Referer": f"https://space.bilibili.com/{mid}"}
        payload = await signed_get(self._client, ACC_INFO_URL, params, headers=headers)
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def get_stat(self, mid: int) -> dict[str, Any]:
        payload = await self._client.get(RELATION_STAT_URL, params={"vmid": mid})
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def get_videos(
        self,
        mid: int,
        *,
        pn: int = 1,
        ps: int = 30,
        order: str = "pubdate",
        keyword: str = "",
        tid: int = 0,
    ) -> dict[str, Any]:
        params = {
            "mid": mid,
            "pn": pn,
            "ps": ps,
            "order": order,
            "keyword": keyword,
            "tid": tid,
            "platform": "web",
            "web_location": "1550101",
        }
        headers = {"Referer": f"https://space.bilibili.com/{mid}/video"}
        payload = await signed_get(self._client, ARC_SEARCH_URL, params, headers=headers)
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}
