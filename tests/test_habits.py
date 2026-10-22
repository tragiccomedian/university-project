"""Tests for Habits, checkins, and streak calculations."""

import uuid
from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.core.errors import ConflictError
from app.models.habit import Habit
from app.models.habit_checkin import HabitCheckin
from app.models.user import User
from app.schemas.habit import HabitCheckinCreate
from app.services.habit import HabitService


@pytest.mark.asyncio
async def test_duplicate_checkin_same_day_raises_conflict() -> None:
    """Checking in twice for the same date must raise ConflictError."""
    session = AsyncMock()
    service = HabitService(session)

    user = User(id=uuid.uuid4(), email="user@test.com", username="testuser", display_name="Test")
    habit = Habit(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Exercise daily",
        frequency="daily",
        target_count=1,
    )
    service.habit_repo.get = AsyncMock(return_value=habit)

    # Mock that a checkin already exists for today
    today = date.today()
    existing_checkin = HabitCheckin(id=uuid.uuid4(), habit_id=habit.id, checkin_date=today, count=1)
    service.checkin_repo.get_by_date = AsyncMock(return_value=existing_checkin)

    with pytest.raises(ConflictError):
        await service.record_checkin(
            habit_id=habit.id,
            user=user,
            data=HabitCheckinCreate(checkin_date=today, count=1),
        )


@pytest.mark.asyncio
async def test_habit_stats_calculation() -> None:
    """Stats correctly computes 30-day completion rate."""
    session = AsyncMock()
    service = HabitService(session)

    user = User(id=uuid.uuid4(), email="user@test.com", username="testuser", display_name="Test")
    habit = Habit(
        id=uuid.uuid4(),
        user_id=user.id,
        title="Drink water",
        frequency="daily",
        target_count=1,
        current_streak=10,
        longest_streak=15,
    )
    service.habit_repo.get = AsyncMock(return_value=habit)
    service.checkin_repo.count_checkins_since = AsyncMock(return_value=15)  # 15 checkins in 30 days
    service.checkin_repo.count_total = AsyncMock(return_value=50)

    stats = await service.get_stats(habit_id=habit.id, user=user)

    assert stats.current_streak == 10
    assert stats.longest_streak == 15
    assert stats.total_checkins == 50
    # 15 / 30 = 50.0%
    assert stats.completion_rate_30d == 50.0
