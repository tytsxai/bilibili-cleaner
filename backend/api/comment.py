from __future__ import annotations

from typing import Any

from .client import BiliApiClient

DELETE_COMMENT_URL = "https://api.bilibili.com/x/v2/reply/del"
REPLY_HISTORY_URL = "https://api.bilibili.com/x/msgfeed/reply"


class CommentApi:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def get_reply_history(self, cursor_id: int = 0) -> dict[str, Any]:
        """获取评论回复历史（包含自己发的评论）"""
        params: dict[str, Any] = {"platform": "web"}
        if cursor_id > 0:
            params["id"] = cursor_id
        payload = await self._client.get(REPLY_HISTORY_URL, params=params)
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def delete_comment(self, comment_type: int, oid: int, rpid: int) -> dict[str, Any]:
        payload = await self._client.post(
            DELETE_COMMENT_URL,
            data={"type": comment_type, "oid": oid, "rpid": rpid},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}
