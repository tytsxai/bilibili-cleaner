from __future__ import annotations

import hashlib
import time
import urllib.parse
from typing import Any, Mapping

from .client import BiliApiClient, BiliApiError

NAV_URL = "https://api.bilibili.com/x/web-interface/nav"

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
