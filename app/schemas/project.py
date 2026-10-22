"""Project schemas."""

import uuid
from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.base import AppBaseModel, TimestampSchema

ProjectStatus = Literal["active", "archived", "completed"]


class ProjectCreate(AppBaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    color: str | None = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectCreate":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date.")
        return self


class ProjectUpdate(AppBaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    status: ProjectStatus | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self) -> "ProjectUpdate":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date.")
        return self


class ProjectRead(TimestampSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    color: str | None
    start_date: date | None
    end_date: date | None
