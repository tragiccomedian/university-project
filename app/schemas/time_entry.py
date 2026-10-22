"""Time tracking schemas."""

import uuid
from datetime import datetime

from pydantic import Field, model_validator

from app.schemas.auth import UserPublic
from app.schemas.base import AppBaseModel, TimestampSchema


class TimeEntryStart(AppBaseModel):
    description: str | None = Field(default=None, max_length=1000)


class TimeEntryManualCreate(AppBaseModel):
    task_id: uuid.UUID
    started_at: datetime
    ended_at: datetime
    description: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_timer_bounds(self) -> "TimeEntryManualCreate":
        if self.ended_at <= self.started_at:
            raise ValueError("ended_at must be strictly greater than started_at.")
        return self


class TimeEntryUpdate(AppBaseModel):
    started_at: datetime | None = None
    ended_at: datetime | None = None
    description: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_timer_bounds(self) -> "TimeEntryUpdate":
        if self.started_at and self.ended_at and self.ended_at <= self.started_at:
            raise ValueError("ended_at must be strictly greater than started_at.")
        return self


class TimeEntryRead(TimestampSchema):
    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    description: str | None
    is_running: bool
    user: UserPublic | None = None
