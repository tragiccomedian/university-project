"""Tests for Time Tracking, active timers, and negative concurrency cases."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.core.errors import NotFoundError, TimerAlreadyRunningError
from app.models.time_entry import TimeEntry
from app.models.user import User
from app.schemas.time_entry import TimeEntryManualCreate
from app.services.time_tracking import TimeTrackingService


def test_time_entry_manual_schema_validation() -> None:
    """ended_at must be strictly greater than started_at."""
    now = datetime.now(UTC)
    earlier = now - timedelta(hours=1)

    with pytest.raises(ValidationError):
        TimeEntryManualCreate(
            task_id=uuid.uuid4(),
            started_at=now,
            ended_at=earlier,  # Invalid: ended before started
        )


@pytest.mark.asyncio
async def test_start_timer_negative_already_running() -> None:
    """Starting a timer while one is already active raises TimerAlreadyRunningError."""
    session = AsyncMock()
    service = TimeTrackingService(session)

    user = User(id=uuid.uuid4(), email="user@test.com", username="testuser", display_name="Test")

    # Mock an existing active timer
    existing_timer = TimeEntry(
        id=uuid.uuid4(),
        task_id=uuid.uuid4(),
        user_id=user.id,
        started_at=datetime.now(UTC),
        is_running=True,
    )
    service.time_repo.get_active_timer = AsyncMock(return_value=existing_timer)

    from app.schemas.time_entry import TimeEntryStart

    with pytest.raises(TimerAlreadyRunningError):
        await service.start_timer(
            workspace_id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            user=user,
            data=TimeEntryStart(),
        )


@pytest.mark.asyncio
async def test_stop_timer_negative_no_active() -> None:
    """Stopping a timer when none is active raises NotFoundError."""
    session = AsyncMock()
    service = TimeTrackingService(session)
    user = User(id=uuid.uuid4(), email="user@test.com", username="testuser", display_name="Test")

    service.time_repo.get_active_timer = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.stop_timer(user)
