from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_REFERER = "https://www.bilibili.com/"


class BiliApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        code: int | None = None,
        data: Any | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.data = data
        self.status_code = status_code


class BiliApiClient:
    def __init__(
        self,
        sessdata: str | None = None,
        bili_jct: str | None = None,
        user_agent: str | None = None,
        referer: str | None = None,
        timeout: float | httpx.Timeout = 10.0,
        qps: float | None = None,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
    ) -> None:
        if qps is not None and qps <= 0:
            raise ValueError("qps must be positive")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")

        headers = {
            "User-Agent": user_agent or DEFAULT_USER_AGENT,
            "Referer": referer or DEFAULT_REFERER,
        }
        cookies: dict[str, str] = {}
        if sessdata:
            cookies["SESSDATA"] = sessdata
        if bili_jct:
            cookies["bili_jct"] = bili_jct
        self._client = httpx.AsyncClient(headers=headers, cookies=cookies, timeout=timeout)
        self._qps = qps
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay
        self._wbi_keys: tuple[str, str] | None = None
        self._wbi_lock = asyncio.Lock()

    async def get_wbi_keys(self) -> tuple[str, str]:
        if self._wbi_keys is not None:
            return self._wbi_keys

        from . import wbi

        shared = wbi.cached_keys()
        if shared is not None:
            self._wbi_keys = shared
            return shared

        async with self._wbi_lock:
            if self._wbi_keys is None:
                shared = wbi.cached_keys()
                if shared is None:
                    shared = await wbi.fetch_wbi_keys(self)
                    wbi.store_keys(shared)
                self._wbi_keys = shared
            return self._wbi_keys

    def invalidate_wbi_keys(self) -> None:
        from . import wbi

        self._wbi_keys = None
        wbi.invalidate_cache()

    async def __aenter__(self) -> BiliApiClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @property
    def csrf_token(self) -> str | None:
        token = self._client.cookies.get("bili_jct")
        return str(token) if token else None

    def set_cookies(self, sessdata: str | None = None, bili_jct: str | None = None) -> None:
        if sessdata is not None:
            self._client.cookies.set("SESSDATA", sessdata)
        if bili_jct is not None:
            self._client.cookies.set("bili_jct", bili_jct)

    def _inject_csrf(self, data: Mapping[str, Any] | None) -> dict[str, Any]:
        payload = dict(data or {})
        token = self.csrf_token
        if token:
            payload.setdefault("csrf", token)
            payload.setdefault("csrf_token", token)
        return payload

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        json: Any | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        from .retry import is_risk_control_error, sleep_backoff

        last_exc: BiliApiError | None = None
        for attempt in range(self._max_retries + 1):
            if self._qps is not None:
                from .ratelimit import get_shared_bucket

                await get_shared_bucket(self._qps).acquire()
            try:
                return await self._request_once(
                    method, url, params=params, data=data, json=json, headers=headers
                )
            except BiliApiError as exc:
                if attempt >= self._max_retries or not is_risk_control_error(exc):
                    raise
                last_exc = exc
                await sleep_backoff(attempt, self._retry_base_delay)
        assert last_exc is not None
        raise last_exc

    async def _request_once(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None,
        data: Mapping[str, Any] | None,
        json: Any | None,
        headers: Mapping[str, str] | None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(
                method,
                url,
                params=params,
                data=data,
                json=json,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise BiliApiError(
                f"HTTP error {exc.response.status_code}",
                status_code=exc.response.status_code,
                data=exc.response.text,
            ) from exc
        except httpx.HTTPError as exc:
            raise BiliApiError(f"HTTP request failed: {exc!s}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BiliApiError("Invalid JSON response", data=response.text) from exc

        if not isinstance(payload, dict):
            raise BiliApiError("Unexpected response payload", data=payload)
        if "code" not in payload:
            raise BiliApiError("Missing code in response", data=payload)
        if payload["code"] != 0:
            message = payload.get("message") or payload.get("msg") or "Bili API error"
            raise BiliApiError(message, code=payload.get("code"), data=payload)
        return payload

    async def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        return await self.request_json("GET", url, params=params, headers=headers)

    async def post(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        json: Any | None = None,
        headers: Mapping[str, str] | None = None,
        include_csrf: bool = False,
    ) -> dict[str, Any]:
        body = self._inject_csrf(data) if include_csrf else data
        return await self.request_json(
            "POST",
            url,
            params=params,
            data=body,
            json=json,
            headers=headers,
        )

    async def close(self) -> None:
        await self._client.aclose()
