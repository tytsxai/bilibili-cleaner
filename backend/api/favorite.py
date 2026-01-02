from __future__ import annotations

from typing import Any, Sequence

from .client import BiliApiClient

FOLDERS_URL = "https://api.bilibili.com/x/v3/fav/folder/created/list-all"
RESOURCE_IDS_URL = "https://api.bilibili.com/x/v3/fav/resource/ids"
BATCH_DELETE_URL = "https://api.bilibili.com/x/v3/fav/resource/batch/del"


class FavoriteApi:
    def __init__(self, client: BiliApiClient) -> None:
        self._client = client

    async def get_folders(self, mid: int) -> dict[str, Any]:
        payload = await self._client.get(FOLDERS_URL, params={"up_mid": mid})
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    async def get_folder_ids(self, media_id: int) -> list[int]:
        payload = await self._client.get(RESOURCE_IDS_URL, params={"media_id": media_id})
        data = payload.get("data") if isinstance(payload, dict) else None
        ids = data.get("ids") if isinstance(data, dict) else None
        if not isinstance(ids, list):
            return []
        results: list[int] = []
        for item in ids:
            try:
                results.append(int(item))
            except (TypeError, ValueError):
                continue
        return results

    async def batch_delete(self, media_id: int, resources: Sequence[str] | str) -> dict[str, Any]:
        if isinstance(resources, str):
            resources_value = resources
        else:
            resources_value = ",".join(str(item) for item in resources)
        payload = await self._client.post(
            BATCH_DELETE_URL,
            data={"media_id": media_id, "resources": resources_value},
            include_csrf=True,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}
