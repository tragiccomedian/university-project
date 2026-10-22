"""Note schemas."""

import uuid

from pydantic import Field

from app.schemas.auth import UserPublic
from app.schemas.base import AppBaseModel, TimestampSchema


class NoteCreate(AppBaseModel):
    workspace_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(default="", max_length=50000)
    is_personal: bool = True


class NoteUpdate(AppBaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    content: str | None = Field(default=None, max_length=50000)
    is_personal: bool | None = None


class NoteRead(TimestampSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    workspace_id: uuid.UUID | None
    title: str
    content: str
    is_personal: bool
    user: UserPublic | None = None
