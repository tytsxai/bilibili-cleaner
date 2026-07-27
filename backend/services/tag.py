from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from backend.api import RelationTagApi
from backend.api.client import BiliApiClient


class TagService:
    def __init__(self, client: BiliApiClient) -> None:
        self._api = RelationTagApi(client)

    async def list_tags(self) -> list[dict[str, Any]]:
        return await self._api.list_tags()

    async def create_tag(self, name: str) -> dict[str, Any]:
        return await self._api.create_tag(name)

    async def delete_tag(self, tagid: int) -> dict[str, Any]:
        return await self._api.delete_tag(tagid)

    async def rename_tag(self, tagid: int, name: str) -> dict[str, Any]:
        return await self._api.rename_tag(tagid, name)

    async def tag_users(
        self,
        mids: Sequence[int],
        *,
        tagid: int | None = None,
        tag_name: str | None = None,
        replace: bool = False,
    ) -> dict[str, Any]:
        """Add ``mids`` to a tag. If ``tag_name`` is given and ``tagid`` is not,
        find or create the tag first. ``replace=True`` calls moveUsers (resets
        each user's tag set); default is copyUsers (preserves existing tags)."""
        if tagid is None and tag_name is None:
            raise ValueError("either tagid or tag_name must be provided")
        if tagid is None:
            assert tag_name is not None
            existing = await self._api.list_tags()
            match = next((t for t in existing if t.get("name") == tag_name), None)
            if match is not None:
                tagid = int(match["tagid"])
            else:
                created = await self._api.create_tag(tag_name)
                tagid = int(created.get("tagid"))
        if replace:
            result = await self._api.move_users_to_tag(mids, [tagid])
        else:
            result = await self._api.copy_users_to_tag(mids, [tagid])
        return {"tagid": tagid, "count": len(mids), "raw": result}

    async def list_tag_users(
        self, tagid: int, *, page: int = 1, page_size: int = 20
    ) -> list[dict[str, Any]]:
        return await self._api.list_tag_users(tagid, pn=page, ps=page_size)
