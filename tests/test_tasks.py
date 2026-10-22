"""Tests for Tasks, Subtasks, Optimistic Locking, and Cycles."""

import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


def test_task_schema_date_validation() -> None:
    """due_date before start_date must raise ValidationError in Pydantic."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    with pytest.raises(ValidationError):
        TaskCreate(
            project_id=uuid.uuid4(),
            title="Invalid Task",
            start_date=today,
            due_date=yesterday,  # Invalid: due before start!
        )


def test_task_update_requires_version() -> None:
    """TaskUpdate schema requires version field for optimistic locking."""
    with pytest.raises(ValidationError):
        # Missing required 'version' field
        TaskUpdate.model_validate({"title": "New Title"})


@pytest.mark.asyncio
async def test_would_create_cycle_self_parent() -> None:
    """A task cannot be its own parent."""
    session = AsyncMock()
    repo = TaskRepository(session)
    task_id = uuid.uuid4()

    is_cycle = await repo.would_create_cycle(task_id=task_id, candidate_parent_id=task_id)
    assert is_cycle is True
