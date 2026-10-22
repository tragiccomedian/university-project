"""Habit and HabitCheckin schemas."""

import uuid
from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.base import AppBaseModel, TimestampSchema

HabitFrequency = Literal["daily", "weekly"]


class HabitCreate(AppBaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    frequency: HabitFrequency = "daily"
    target_count: int = Field(default=1, ge=1)


class HabitUpdate(AppBaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    frequency: HabitFrequency | None = None
    target_count: int | None = Field(default=None, ge=1)


class HabitRead(TimestampSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    frequency: HabitFrequency
    target_count: int
    current_streak: int
    longest_streak: int
    streak_last_updated: date | None


class HabitCheckinCreate(AppBaseModel):
    checkin_date: date | None = None
    count: int = Field(default=1, ge=1)


class HabitCheckinRead(AppBaseModel):
    id: uuid.UUID
    habit_id: uuid.UUID
    checkin_date: date
    count: int
    created_at: date


class HabitStats(AppBaseModel):
    habit_id: uuid.UUID
    title: str
    current_streak: int
    longest_streak: int
    total_checkins: int
    completion_rate_30d: float
