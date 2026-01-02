from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from backend.api import CommentApi, DynamicApi, FavoriteApi, HistoryApi, RelationApi
from backend.api.client import BiliApiClient


@dataclass(frozen=True)
class CleanResult:
    count: int


class CleanerService:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client
        self._relation_api = RelationApi(client)
        self._favorite_api = FavoriteApi(client)
        self._dynamic_api = DynamicApi(client)
        self._history_api = HistoryApi(client)
        self._comment_api = CommentApi(client)

    async def clear_all_followings(self, mid: int) -> CleanResult:
        total = 0
        safety = 0
        while True:
            data = await self._relation_api.get_followings(mid, pn=1, ps=50)
            mids = self._extract_following_mids(data)
            if not mids:
                break
            for batch in _chunked(mids, 50):
                await self._relation_api.batch_unfollow(batch)
                total += len(batch)
            safety += 1
            if safety > 200:
                break
        return CleanResult(total)

    async def clear_all_favorites(self, mid: int) -> CleanResult:
        total = 0
        data = await self._favorite_api.get_folders(mid)
        folders = data.get("list") if isinstance(data, dict) else None
        if not isinstance(folders, list):
            return CleanResult(0)
        for folder in folders:
            if not isinstance(folder, Mapping):
                continue
            media_id = _safe_int(folder.get("id") or folder.get("media_id"))
            if media_id is None:
                continue
            resource_ids = await self._favorite_api.get_folder_ids(media_id)
            if not resource_ids:
                continue
            resources = [f"{item}:2" for item in resource_ids]
            for batch in _chunked(resources, 100):
                await self._favorite_api.batch_delete(media_id, batch)
                total += len(batch)
        return CleanResult(total)

    async def clear_all_dynamics(self, mid: int) -> CleanResult:
        total = 0
        offset: str | None = None
        safety = 0
        while True:
            data = await self._dynamic_api.get_dynamics(mid, offset=offset)
            items = data.get("items") if isinstance(data, dict) else None
            if not isinstance(items, list) or not items:
                break
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                dynamic_id = _extract_dynamic_id(item)
                if dynamic_id is None:
                    continue
                await self._dynamic_api.delete_dynamic(dynamic_id)
                total += 1
            has_more = bool(data.get("has_more")) if isinstance(data, dict) else False
            next_offset = data.get("offset") if isinstance(data, dict) else None
            if not has_more or not next_offset or next_offset == offset:
                break
            offset = str(next_offset)
            safety += 1
            if safety > 200:
                break
        return CleanResult(total)

    async def clear_history(self) -> CleanResult:
        await self._history_api.clear_history()
        return CleanResult(0)

    async def clear_all_comments(self) -> CleanResult:
        """清理用户发布的评论（通过回复历史获取）"""
        total = 0
        cursor_id = 0
        safety = 0
        while True:
            data = await self._comment_api.get_reply_history(cursor_id)
            items = data.get("items") if isinstance(data, dict) else None
            if not isinstance(items, list) or not items:
                break
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                # 提取评论信息
                item_data = item.get("item") if isinstance(item, Mapping) else None
                if not isinstance(item_data, dict):
                    continue
                oid = _safe_int(item_data.get("subject_id"))
                rpid = _safe_int(item_data.get("target_reply_id"))
                comment_type = _safe_int(item_data.get("business_id")) or 1
                if oid and rpid:
                    try:
                        await self._comment_api.delete_comment(comment_type, oid, rpid)
                        total += 1
                    except Exception:
                        pass
            # 获取下一页游标
            cursor = data.get("cursor") if isinstance(data, dict) else None
            if not isinstance(cursor, dict):
                break
            next_id = _safe_int(cursor.get("id"))
            is_end = cursor.get("is_end", True)
            if is_end or not next_id or next_id == cursor_id:
                break
            cursor_id = next_id
            safety += 1
            if safety > 100:
                break
        return CleanResult(total)

    @staticmethod
    def _extract_following_mids(data: Mapping[str, Any]) -> list[int]:
        items = data.get("list") if isinstance(data, Mapping) else None
        if not isinstance(items, list):
            return []
        mids: list[int] = []
        for item in items:
            if not isinstance(item, Mapping):
                continue
            mid_value = _safe_int(item.get("mid"))
            if mid_value is not None:
                mids.append(mid_value)
        return mids


def _extract_dynamic_id(item: Mapping[str, Any]) -> int | None:
    for key in ("id_str", "id", "dynamic_id", "dyn_id"):
        if key not in item:
            continue
        value = item.get(key)
        dynamic_id = _safe_int(value)
        if dynamic_id is not None:
            return dynamic_id
    return None


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _chunked(items: Sequence[Any], size: int) -> Iterable[list[Any]]:
    for index in range(0, len(items), size):
        yield list(items[index : index + size])
