from __future__ import annotations

import hashlib
import logging
import time
import urllib.parse
from collections.abc import Mapping
from typing import Any

from .client import BiliApiClient, BiliApiError

logger = logging.getLogger(__name__)

NAV_URL = "https://api.bilibili.com/x/web-interface/nav"

# WBI keys are global to B 站, not per-account, and rotate roughly daily. The
# HTTP layer builds a fresh client per request, so without a process-level
# cache every signed call pays for an extra /nav request — doubling the
# requests charged against the shared rate limit and against risk control.
_WBI_CACHE_TTL = 3600.0
_cached_keys: tuple[str, str] | None = None
_cached_at: float = 0.0


def cached_keys() -> tuple[str, str] | None:
    """Return the process-wide keys if they are still fresh."""
    if _cached_keys is None:
        return None
    if time.monotonic() - _cached_at > _WBI_CACHE_TTL:
        return None
    return _cached_keys


def store_keys(keys: tuple[str, str]) -> None:
    global _cached_keys, _cached_at
    _cached_keys = keys
    _cached_at = time.monotonic()


def invalidate_cache() -> None:
    global _cached_keys
    _cached_keys = None

_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
]


def _extract_key(url: str) -> str:
    name = url.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[0]


def _mixin_key(img_key: str, sub_key: str) -> str:
    raw = img_key + sub_key
    return "".join(raw[i] for i in _MIXIN_KEY_ENC_TAB if i < len(raw))[:32]


async def fetch_wbi_keys(client: BiliApiClient) -> tuple[str, str]:
    payload = await client.get(NAV_URL)
    data = payload.get("data") if isinstance(payload, dict) else None
    wbi = data.get("wbi_img") if isinstance(data, Mapping) else None
    if not isinstance(wbi, Mapping):
        raise BiliApiError("Missing wbi_img in nav response", data=payload)
    img_url = wbi.get("img_url")
    sub_url = wbi.get("sub_url")
    if not img_url or not sub_url:
        raise BiliApiError("Missing wbi urls", data=payload)
    return _extract_key(str(img_url)), _extract_key(str(sub_url))


def sign_params(params: Mapping[str, Any], img_key: str, sub_key: str) -> dict[str, Any]:
    mixin = _mixin_key(img_key, sub_key)
    wts = int(time.time())
    signed: dict[str, Any] = dict(params)
    signed["wts"] = wts
    items = sorted(signed.items(), key=lambda kv: kv[0])
    query = urllib.parse.urlencode(items, doseq=True)
    signed["w_rid"] = hashlib.md5((query + mixin).encode("utf-8")).hexdigest()
    return signed


async def signed_get(
    client: BiliApiClient,
    url: str,
    params: Mapping[str, Any],
    *,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """GET ``url`` with WBI signature using ``client``'s cached keys.

    If the request fails with a WBI-related error code we refresh the keys
    once and retry. Other errors propagate.
    """
    img_key, sub_key = await client.get_wbi_keys()
    signed = sign_params(params, img_key, sub_key)
    try:
        return await client.get(url, params=signed, headers=headers)
    except BiliApiError as exc:
        if exc.code not in {-101, -111, -403}:
            raise
        client.invalidate_wbi_keys()
        img_key, sub_key = await client.get_wbi_keys()
        signed = sign_params(params, img_key, sub_key)
        return await client.get(url, params=signed, headers=headers)
