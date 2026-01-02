from __future__ import annotations

from typing import Any

from .client import BiliApiClient

DELETE_COMMENT_URL = "https://api.bilibili.com/x/v2/reply/del"


class CommentApi:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def delete_comment(self, comment_type: int, oid: int, rpid: int) -> dict[str, Any]:
        payload = await self._client.post(
            DELETE_COMMENT_URL,
            data={"type": comment_type, "oid": oid, "rpid": rpid},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}
