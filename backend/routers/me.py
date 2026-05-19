from __future__ import annotations

from fastapi import APIRouter

from backend.api import AuthApi
from backend.schemas import SelfInfo

from ._deps import AuthDep, authed_client

router = APIRouter(prefix="/me", tags=["me"])


@router.get(
    "",
    response_model=SelfInfo,
    summary="Get the currently authenticated user",
)
async def get_me(auth: tuple[str, str] = AuthDep) -> SelfInfo:
    """Return ``{isLogin, mid, uname, ...}`` for the SESSDATA in headers.

    Use this as the first call in any AI workflow — it both verifies the
    session and gives you the ``mid`` needed by other endpoints.
    """
    async with authed_client(auth) as client:
        api = AuthApi(client)
        data = await api.get_self_info()
    return SelfInfo(
        isLogin=bool(data.get("isLogin", False)),
        mid=data.get("mid"),
        uname=data.get("uname"),
        raw=data,
    )
