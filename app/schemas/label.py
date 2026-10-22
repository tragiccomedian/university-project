"""Label schemas."""

import uuid

from pydantic import Field

from app.schemas.base import AppBaseModel, TimestampSchema


class LabelCreate(AppBaseModel):
    name: str = Field(min_length=1, max_length=50)
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")


class LabelUpdate(AppBaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class LabelRead(TimestampSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    color: str
