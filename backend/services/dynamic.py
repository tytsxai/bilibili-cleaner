from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Sequence

from backend.api import DynamicApi
from backend.api.client import BiliApiClient
from ._utils import extract_dynamic_id, safe_int

logger = logging.getLogger(__name__)


class DynamicService:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client
        self._api = DynamicApi(client)

    async def list_page(
        self, mid: int, offset: str | None = None
    ) -> dict[str, Any]:
        return await self._api.get_dynamics(mid, offset=offset)

    async def iter_all(self, mid: int) -> AsyncIterator[dict[str, Any]]:
        offset: str | None = None
        safety = 0
        while True:
            data = await self._api.get_dynamics(mid, offset=offset)
            items = data.get("items") if isinstance(data, dict) else None
            if not isinstance(items, list) or not items:
                return
            for item in items:
                if isinstance(item, dict):
                    yield item
            has_more = bool(data.get("has_more")) if isinstance(data, dict) else False
            next_offset = data.get("offset") if isinstance(data, dict) else None
            if not has_more or not next_offset or next_offset == offset:
                return
            offset = str(next_offset)
            safety += 1
            if safety > 500:
                logger.warning("iter_all reached safety limit on mid %s", mid)
                return

    async def delete_many(
        self,
        ids: Sequence[int | str],
        *,
        on_item: "object | None" = None,
    ) -> dict[str, Any]:
        ok = 0
        errors: list[dict[str, Any]] = []
        for raw in ids:
            dynamic_id = safe_int(raw)
            if dynamic_id is None:
                errors.append({"id": str(raw), "type": "ValueError", "message": "invalid id"})
                continue
            try:
                await self._api.delete_dynamic(dynamic_id)
                ok += 1
                if on_item is not None:
                    on_item(dynamic_id, True, None)
            except Exception as exc:
                err = {"id": dynamic_id, "type": type(exc).__name__, "message": str(exc)}
                errors.append(err)
                if on_item is not None:
                    on_item(dynamic_id, False, err)
        return {"ok": ok, "errors": errors, "total": len(ids)}

    async def clear_all(
        self, mid: int, *, on_item: "object | None" = None
    ) -> dict[str, Any]:
        ok = 0
        errors: list[dict[str, Any]] = []
        offset: str | None = None
        safety = 0
        while True:
            data = await self._api.get_dynamics(mid, offset=offset)
            items = data.get("items") if isinstance(data, dict) else None
            if not isinstance(items, list) or not items:
                break
            for item in items:
                dynamic_id = extract_dynamic_id(item) if isinstance(item, dict) else None
                if dynamic_id is None:
                    continue
                try:
                    await self._api.delete_dynamic(dynamic_id)
                    ok += 1
                    if on_item is not None:
                        on_item(dynamic_id, True, None)
                except Exception as exc:
                    err = {"id": dynamic_id, "type": type(exc).__name__, "message": str(exc)}
                    errors.append(err)
                    if on_item is not None:
                        on_item(dynamic_id, False, err)
            has_more = bool(data.get("has_more")) if isinstance(data, dict) else False
            next_offset = data.get("offset") if isinstance(data, dict) else None
            if not has_more or not next_offset or next_offset == offset:
                break
            offset = str(next_offset)
            safety += 1
            if safety > 200:
                break
        return {"ok": ok, "errors": errors}
