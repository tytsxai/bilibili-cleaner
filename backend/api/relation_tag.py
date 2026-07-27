from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .client import BiliApiClient

LIST_TAGS_URL = "https://api.bilibili.com/x/relation/tags"
CREATE_TAG_URL = "https://api.bilibili.com/x/relation/tag/create"
DELETE_TAG_URL = "https://api.bilibili.com/x/relation/tag/del"
UPDATE_TAG_URL = "https://api.bilibili.com/x/relation/tag/update"
COPY_USERS_URL = "https://api.bilibili.com/x/relation/tags/copyUsers"
MOVE_USERS_URL = "https://api.bilibili.com/x/relation/tags/moveUsers"
ADD_USERS_URL = "https://api.bilibili.com/x/relation/tags/addUsers"
TAG_USERS_URL = "https://api.bilibili.com/x/relation/tag"


def _csv(values: Sequence[int]) -> str:
    return ",".join(str(v) for v in values)


class RelationTagApi:
    """Custom following groups (B 站「关注分组」)."""

    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def list_tags(self) -> list[dict[str, Any]]:
        payload = await self._client.get(LIST_TAGS_URL)
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, list) else []

    async def create_tag(self, name: str) -> dict[str, Any]:
        payload = await self._client.post(
            CREATE_TAG_URL,
            data={"tag": name},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def delete_tag(self, tagid: int) -> dict[str, Any]:
        payload = await self._client.post(
            DELETE_TAG_URL,
            data={"tagid": tagid},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def rename_tag(self, tagid: int, name: str) -> dict[str, Any]:
        payload = await self._client.post(
            UPDATE_TAG_URL,
            data={"tagid": tagid, "name": name},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def copy_users_to_tag(
        self, mids: Sequence[int], tagids: Sequence[int]
    ) -> dict[str, Any]:
        """Add ``mids`` to the given ``tagids`` without removing existing tags."""
        payload = await self._client.post(
            COPY_USERS_URL,
            data={"fids": _csv(mids), "tagids": _csv(tagids)},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def move_users_to_tag(
        self, mids: Sequence[int], tagids: Sequence[int]
    ) -> dict[str, Any]:
        """Replace each user's tag set with ``tagids``."""
        payload = await self._client.post(
            MOVE_USERS_URL,
            data={"fids": _csv(mids), "tagids": _csv(tagids)},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def list_tag_users(
        self, tagid: int, *, pn: int = 1, ps: int = 20
    ) -> list[dict[str, Any]]:
        payload = await self._client.get(
            TAG_USERS_URL,
            params={"tagid": tagid, "pn": pn, "ps": ps},
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, list) else []
