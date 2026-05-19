from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Iterable, Mapping, Sequence

from backend.api import FavoriteApi
from backend.api.client import BiliApiClient
from ._utils import chunked, safe_int

logger = logging.getLogger(__name__)


class FavoriteService:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client
        self._api = FavoriteApi(client)

    async def list_folders(self, mid: int) -> list[dict[str, Any]]:
        data = await self._api.get_folders(mid)
        folders = data.get("list") if isinstance(data, dict) else None
        return [f for f in folders if isinstance(f, dict)] if isinstance(folders, list) else []

    async def list_items(
        self,
        media_id: int,
        *,
        page: int = 1,
        page_size: int = 20,
        keyword: str = "",
        order: str = "mtime",
    ) -> dict[str, Any]:
        return await self._api.list_resources(
            media_id, pn=page, ps=page_size, keyword=keyword, order=order
        )

    async def iter_items(
        self,
        media_id: int,
        *,
        page_size: int = 20,
        order: str = "mtime",
    ) -> AsyncIterator[dict[str, Any]]:
        page = 1
        safety = 0
        while True:
            data = await self.list_items(
                media_id, page=page, page_size=page_size, order=order
            )
            medias = data.get("medias") if isinstance(data, dict) else None
            if not isinstance(medias, list) or not medias:
                return
            for item in medias:
                if isinstance(item, dict):
                    yield item
            if len(medias) < page_size:
                return
            page += 1
            safety += 1
            if safety > 500:
                logger.warning("iter_items reached safety limit on folder %s", media_id)
                return

    async def delete_resources(
        self,
        media_id: int,
        resources: Sequence[Mapping[str, Any] | str | int],
        *,
        on_batch: "object | None" = None,
    ) -> dict[str, Any]:
        """Delete arbitrary items from ``media_id``.

        Items may be ``"<id>:<type>"`` strings, plain ints (assumed type=2 video),
        or dicts ``{id, type}``.
        """
        formatted: list[str] = []
        for item in resources:
            if isinstance(item, str):
                formatted.append(item)
            elif isinstance(item, int):
                formatted.append(f"{item}:2")
            elif isinstance(item, Mapping):
                rid = item.get("id")
                rtype = item.get("type", 2)
                if rid is None:
                    continue
                formatted.append(f"{rid}:{rtype}")
        ok = 0
        errors: list[dict[str, Any]] = []
        for batch in chunked(formatted, 100):
            try:
                await self._api.batch_delete(media_id, batch)
                ok += len(batch)
                if on_batch is not None:
                    on_batch(media_id, batch, None)
            except Exception as exc:
                err = {"media_id": media_id, "type": type(exc).__name__, "message": str(exc)}
                errors.append(err)
                if on_batch is not None:
                    on_batch(media_id, batch, err)
        return {"ok": ok, "errors": errors, "total": len(formatted)}

    async def clear_all(
        self,
        mid: int,
        *,
        on_batch: "object | None" = None,
    ) -> dict[str, Any]:
        total_ok = 0
        errors: list[dict[str, Any]] = []
        folders = await self.list_folders(mid)
        for folder in folders:
            media_id = safe_int(folder.get("id") or folder.get("media_id"))
            if media_id is None:
                continue
            resource_ids = await self._api.get_folder_ids(media_id)
            if not resource_ids:
                continue
            resources = [f"{item}:2" for item in resource_ids]
            for batch in chunked(resources, 100):
                try:
                    await self._api.batch_delete(media_id, batch)
                    total_ok += len(batch)
                    if on_batch is not None:
                        on_batch(media_id, batch, None)
                except Exception as exc:
                    err = {
                        "media_id": media_id,
                        "type": type(exc).__name__,
                        "message": str(exc),
                    }
                    errors.append(err)
                    if on_batch is not None:
                        on_batch(media_id, batch, err)
        return {"ok": total_ok, "errors": errors}
