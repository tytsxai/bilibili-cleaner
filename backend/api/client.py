from __future__ import annotations

from typing import Any, Mapping

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
    ) -> None:
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

    async def __aenter__(self) -> "BiliApiClient":
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
