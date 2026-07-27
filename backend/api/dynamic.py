from __future__ import annotations

from typing import Any

from .client import BiliApiClient
from .wbi import signed_get

DYNAMICS_URL = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space"
DELETE_DYNAMIC_URL = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/rm_dynamic"

FEATURES = (
    "itemOpusStyle,opusBigCover,onlyfansVote,endFooterHidden,"
    "decorationCard,onlyfansAssetsV2,ugcDelete"
)


class DynamicApi:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def get_dynamics(self, mid: int, offset: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {
            "host_mid": mid,
            "offset": offset or "",
            "timezone_offset": -480,
            "platform": "web",
            "features": FEATURES,
            "web_location": "333.1387",
        }
        headers = {
            "Referer": f"https://space.bilibili.com/{mid}/dynamic",
            "Origin": "https://space.bilibili.com",
        }
        payload = await signed_get(self._client, DYNAMICS_URL, params, headers=headers)
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
