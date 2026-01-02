from __future__ import annotations

from typing import Any

from .client import BiliApiClient, BiliApiError

GENERATE_QRCODE_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
POLL_QRCODE_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"


class AuthApi:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def generate_qrcode(self) -> tuple[str, str]:
        payload = await self._client.get(GENERATE_QRCODE_URL)
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise BiliApiError("Missing QR code payload", data=payload)
        url = data.get("url")
        qrcode_key = data.get("qrcode_key")
        if not url or not qrcode_key:
            raise BiliApiError("Missing QR code fields", data=payload)
        return str(url), str(qrcode_key)

    async def poll_qrcode(self, qrcode_key: str) -> dict[str, Any]:
        payload = await self._client.get(POLL_QRCODE_URL, params={"qrcode_key": qrcode_key})
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}
