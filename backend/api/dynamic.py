from __future__ import annotations

from typing import Any

from .client import BiliApiClient
from .wbi import fetch_wbi_keys, sign_params

DYNAMICS_URL = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space"
DELETE_DYNAMIC_URL = "https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/rm_dynamic"

FEATURES = "itemOpusStyle,opusBigCover,onlyfansVote,endFooterHidden,decorationCard,onlyfansAssetsV2,ugcDelete"


class DynamicApi:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client
        self._wbi_keys: tuple[str, str] | None = None

    async def _get_wbi_keys(self) -> tuple[str, str]:
        if self._wbi_keys is None:
            self._wbi_keys = await fetch_wbi_keys(self._client)
        return self._wbi_keys

    async def get_dynamics(self, mid: int, offset: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {
            "host_mid": mid,
            "offset": offset or "",
            "timezone_offset": -480,
            "platform": "web",
            "features": FEATURES,
            "web_location": "333.1387",
        }
        img_key, sub_key = await self._get_wbi_keys()
        signed = sign_params(params, img_key, sub_key)
        headers = {
            "Referer": f"https://space.bilibili.com/{mid}/dynamic",
            "Origin": "https://space.bilibili.com",
        }
        payload = await self._client.get(DYNAMICS_URL, params=signed, headers=headers)
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
