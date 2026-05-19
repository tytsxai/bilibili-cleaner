from __future__ import annotations

from dataclasses import dataclass

from backend.api.client import BiliApiClient

from .dynamic import DynamicService
from .favorite import FavoriteService
from .following import FollowingService
from .history import HistoryService


@dataclass(frozen=True)
class CleanResult:
    count: int


class CleanerService:
    """Thin v1-compatible wrapper around the per-resource services.

    Preserved for ``/api/clean/*`` legacy endpoints; new work should depend
    on the underlying ``FollowingService`` / ``FavoriteService`` / etc.
    """

    def __init__(self, client: BiliApiClient) -> None:
        self._following = FollowingService(client)
        self._favorite = FavoriteService(client)
        self._dynamic = DynamicService(client)
        self._history = HistoryService(client)

    async def clear_all_followings(self, mid: int) -> CleanResult:
        result = await self._following.clear_all(mid)
        return CleanResult(int(result.get("ok", 0)))

    async def clear_all_favorites(self, mid: int) -> CleanResult:
        result = await self._favorite.clear_all(mid)
        return CleanResult(int(result.get("ok", 0)))

    async def clear_all_dynamics(self, mid: int) -> CleanResult:
        result = await self._dynamic.clear_all(mid)
        return CleanResult(int(result.get("ok", 0)))

    async def clear_history(self) -> CleanResult:
        await self._history.clear()
        return CleanResult(1)
