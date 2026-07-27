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
    errors: int = 0
    stopped_reason: str | None = None

    @property
    def complete(self) -> bool:
        """False when the clean gave up early or hit per-item failures.

        The v1 endpoints used to report ``success: True`` regardless, so a run
        that bailed out after a page of failures looked identical to one that
        actually emptied the account.
        """
        return self.errors == 0 and self.stopped_reason is None


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
        return _to_result(await self._following.clear_all(mid))

    async def clear_all_favorites(self, mid: int) -> CleanResult:
        return _to_result(await self._favorite.clear_all(mid))

    async def clear_all_dynamics(self, mid: int) -> CleanResult:
        return _to_result(await self._dynamic.clear_all(mid))

    async def clear_history(self) -> CleanResult:
        await self._history.clear()
        return CleanResult(1)


def _to_result(raw: dict) -> CleanResult:
    errors = raw.get("errors")
    return CleanResult(
        count=int(raw.get("ok", 0)),
        errors=len(errors) if isinstance(errors, list) else 0,
        stopped_reason=raw.get("stopped_reason"),
    )
