"""Task schemas."""

import uuid
from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.auth import UserPublic
from app.schemas.base import AppBaseModel, TimestampSchema
from app.schemas.label import LabelRead

TaskStatus = Literal["todo", "in_progress", "in_review", "done", "cancelled"]
TaskPriority = Literal["low", "medium", "high", "critical"]


class TaskCreate(AppBaseModel):
    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    parent_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    label_ids: list[uuid.UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> "TaskCreate":
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValueError("start_date cannot be after due_date.")
        return self


class TaskUpdate(AppBaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    parent_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None
    start_date: date | None = None
    due_date: date | None = None
    version: int = Field(..., description="Expected current version for optimistic locking")

    @model_validator(mode="after")
    def validate_dates(self) -> "TaskUpdate":
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValueError("start_date cannot be after due_date.")
        return self


class TaskRead(TimestampSchema):
    id: uuid.UUID
    project_id: uuid.UUID
    workspace_id: uuid.UUID
    parent_id: uuid.UUID | None
    creator_id: uuid.UUID
    assignee_id: uuid.UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    start_date: date | None
    due_date: date | None
    version: int
    labels: list[LabelRead] = Field(default_factory=list)
    assignee: UserPublic | None = None
    creator: UserPublic | None = None


class TaskDetail(TaskRead):
    subtasks: list["TaskRead"] = Field(default_factory=list)


class TaskFilterParams(AppBaseModel):
    project_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    search: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
