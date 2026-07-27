from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any


def safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def chunked(items: Sequence[Any], size: int) -> Iterable[list[Any]]:
    for index in range(0, len(items), size):
        yield list(items[index : index + size])


def extract_dynamic_id(item: Mapping[str, Any]) -> int | None:
    for key in ("id_str", "id", "dynamic_id", "dyn_id"):
        if key not in item:
            continue
        dynamic_id = safe_int(item.get(key))
        if dynamic_id is not None:
            return dynamic_id
    return None


def extract_following_mids(data: Mapping[str, Any]) -> list[int]:
    items = data.get("list") if isinstance(data, Mapping) else None
    if not isinstance(items, list):
        return []
    mids: list[int] = []
    for item in items:
        if not isinstance(item, Mapping):
            continue
        mid_value = safe_int(item.get("mid"))
        if mid_value is not None:
            mids.append(mid_value)
    return mids
