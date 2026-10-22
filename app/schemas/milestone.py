"""Milestone and Timeline schemas."""

import uuid
from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.base import AppBaseModel, TimestampSchema
from app.schemas.task import TaskRead

MilestoneStatus = Literal["pending", "completed", "missed"]


class MilestoneCreate(AppBaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None
    status: MilestoneStatus = "pending"


class MilestoneUpdate(AppBaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None
    status: MilestoneStatus | None = None


class MilestoneRead(TimestampSchema):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    due_date: date | None
    status: MilestoneStatus


class ProjectTimelineRead(AppBaseModel):
    project_id: uuid.UUID
    milestones: list[MilestoneRead]
    tasks: list[TaskRead]
