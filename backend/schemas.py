from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str
    code: int | None = None
    data: Any | None = None


class TaskInfo(BaseModel):
    task_id: str
    kind: str
    status: str = Field(
        ...,
        description="pending | running | completed | failed | cancelled",
    )
    processed: int = 0
    total: int | None = None
    errors: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Recorded errors, truncated to BILI_MAX_TASK_ERRORS entries",
    )
    error_count: int = Field(
        0, description="Total errors seen, including any omitted from `errors`"
    )
    result: dict[str, Any] | None = None
    started_at: float | None = None
    finished_at: float | None = None


class TaskAck(BaseModel):
    task_id: str
    status: str = "pending"


class SelfInfo(BaseModel):
    isLogin: bool = False
    mid: int | None = None
    uname: str | None = None
    raw: dict[str, Any] | None = Field(default=None, description="Full B 站 nav payload")


class FollowingItem(BaseModel):
    mid: int
    uname: str | None = None
    sign: str | None = None
    face: str | None = None
    official_verify: dict[str, Any] | None = None
    raw: dict[str, Any] | None = Field(default=None, description="Full original item from B 站")


class FollowingDetail(BaseModel):
    mid: int
    info: dict[str, Any]
    stat: dict[str, Any]
    latest_video: dict[str, Any] | None = None
    video_count: int | None = None


class FollowingListResponse(BaseModel):
    page: int
    page_size: int
    total: int | None = None
    items: list[dict[str, Any]]


class UnfollowRequest(BaseModel):
    mids: list[int] = Field(..., min_length=1)


class BatchActionResult(BaseModel):
    ok: int
    total: int | None = None
    errors: list[dict[str, Any]] = Field(default_factory=list)


class FolderInfo(BaseModel):
    id: int
    title: str | None = None
    media_count: int | None = None
    raw: dict[str, Any] | None = None


class ResourceRef(BaseModel):
    id: int
    type: int = 2


class DeleteFavoritesRequest(BaseModel):
    resources: list[ResourceRef] = Field(..., min_length=1)


class DeleteDynamicsRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1)


class TagCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class TagUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)


class TagUsersRequest(BaseModel):
    mids: list[int] = Field(..., min_length=1)
    tagid: int | None = None
    tag_name: str | None = None
    replace: bool = False


class CleanAllResult(BaseModel):
    success: bool
    counts: dict[str, int]
    total: int
