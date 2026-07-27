from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Sequence
from typing import Any

from backend import audit
from backend.api import RelationApi, UserApi
from backend.api.client import BiliApiClient, BiliApiError

from ._progress import ItemCallback
from ._utils import extract_following_mids

logger = logging.getLogger(__name__)

MAX_CLEAR_PAGES = 200


class FollowingService:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client
        self._relation_api = RelationApi(client)
        self._user_api = UserApi(client)

    async def list_page(
        self,
        mid: int,
        *,
        page: int = 1,
        page_size: int = 50,
        order: str = "desc",
        order_type: str = "attention",
    ) -> dict[str, Any]:
        return await self._relation_api.get_followings(
            mid, pn=page, ps=page_size, order=order, order_type=order_type
        )

    async def iter_all(
        self,
        mid: int,
        *,
        page_size: int = 50,
        order: str = "desc",
        order_type: str = "attention",
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield each following item across all pages."""
        page = 1
        safety = 0
        while True:
            data = await self._relation_api.get_followings(
                mid, pn=page, ps=page_size, order=order, order_type=order_type
            )
            items = data.get("list") if isinstance(data, dict) else None
            if not isinstance(items, list) or not items:
                return
            for item in items:
                if isinstance(item, dict):
                    yield item
            if len(items) < page_size:
                return
            page += 1
            safety += 1
            if safety > 500:
                logger.warning("iter_all reached safety limit at page=%s", page)
                return

    async def get_detail(self, target_mid: int) -> dict[str, Any]:
        """Combined profile + relation-stat + latest video for a single UP."""
        try:
            info = await self._user_api.get_info(target_mid)
        except BiliApiError as exc:
            info = {"_error": str(exc), "_code": exc.code}
        try:
            stat = await self._user_api.get_stat(target_mid)
        except BiliApiError as exc:
            stat = {"_error": str(exc), "_code": exc.code}
        try:
            videos = await self._user_api.get_videos(target_mid, pn=1, ps=1)
            vlist = videos.get("list", {}).get("vlist") if isinstance(videos, dict) else None
            latest = vlist[0] if isinstance(vlist, list) and vlist else None
            video_count = videos.get("page", {}).get("count") if isinstance(videos, dict) else None
        except BiliApiError as exc:
            latest = {"_error": str(exc), "_code": exc.code}
            video_count = None
        return {
            "mid": target_mid,
            "info": info,
            "stat": stat,
            "latest_video": latest,
            "video_count": video_count,
        }

    async def enrich(
        self,
        mids: Sequence[int],
        *,
        concurrency: int = 3,
    ) -> list[dict[str, Any]]:
        """Fetch detail for many mids in parallel under ``concurrency`` limit."""
        sem = asyncio.Semaphore(concurrency)

        async def one(target: int) -> dict[str, Any]:
            async with sem:
                return await self.get_detail(target)

        return await asyncio.gather(*(one(m) for m in mids))

    async def unfollow_many(
        self,
        mids: Sequence[int],
        *,
        on_item: ItemCallback | None = None,
    ) -> dict[str, Any]:
        """Unfollow each mid sequentially. ``on_item`` is a callable
        ``(mid, ok, error)`` invoked after each attempt for progress tracking."""
        ok = 0
        errors: list[dict[str, Any]] = []
        for target in mids:
            try:
                await self._relation_api.unfollow(target)
                ok += 1
                audit.record("following.unfollow", target, ok=True)
                if on_item is not None:
                    on_item(target, True, None)
            except Exception as exc:
                err = {"mid": target, "type": type(exc).__name__, "message": str(exc)}
                errors.append(err)
                logger.warning("Failed to unfollow mid=%s: %s", target, exc)
                audit.record("following.unfollow", target, ok=False, error=str(exc))
                if on_item is not None:
                    on_item(target, False, err)
        return {"ok": ok, "errors": errors, "total": len(mids)}

    async def clear_all(
        self,
        mid: int,
        *,
        on_item: ItemCallback | None = None,
    ) -> dict[str, Any]:
        ok = 0
        errors: list[dict[str, Any]] = []
        safety = 0
        while True:
            data = await self._relation_api.get_followings(mid, pn=1, ps=50)
            target_mids = extract_following_mids(data)
            if not target_mids:
                break
            page_ok = 0
            for target in target_mids:
                try:
                    await self._relation_api.unfollow(target)
                    ok += 1
                    page_ok += 1
                    audit.record("following.unfollow", target, ok=True)
                    if on_item is not None:
                        on_item(target, True, None)
                except Exception as exc:
                    err = {"mid": target, "type": type(exc).__name__, "message": str(exc)}
                    errors.append(err)
                    logger.warning("Failed to unfollow mid=%s: %s", target, exc)
                    audit.record("following.unfollow", target, ok=False, error=str(exc))
                    if on_item is not None:
                        on_item(target, False, err)
            if page_ok == 0:
                logger.warning(
                    "Stopped clear_all for mid=%s after a page made no progress",
                    mid,
                )
                return {"ok": ok, "errors": errors, "stopped_reason": "no_progress"}
            safety += 1
            if safety > MAX_CLEAR_PAGES:
                # Bailing out here used to look identical to a finished clean,
                # so the caller reported success while followings remained.
                logger.warning(
                    "clear_all for mid=%s hit the %s-page safety limit with items left",
                    mid,
                    MAX_CLEAR_PAGES,
                )
                return {"ok": ok, "errors": errors, "stopped_reason": "page_limit"}
        return {"ok": ok, "errors": errors}
