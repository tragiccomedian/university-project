"""Task repository with optimistic locking and circular dependency validation."""

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from app.models.task import Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    def _query_with_relations(self):  # type: ignore[no-untyped-def]
        return self._base_query().options(
            selectinload(Task.labels),
            selectinload(Task.assignee),
            selectinload(Task.creator),
        )

    async def get_with_relations(self, task_id: uuid.UUID) -> Task | None:
        query = (
            self._query_with_relations()
            .where(Task.id == task_id)
            .options(
                selectinload(Task.subtasks).selectinload(Task.labels),
                selectinload(Task.subtasks).selectinload(Task.assignee),
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        assignee_id: uuid.UUID | None = None,
        status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        """Fetch tasks with filters, FTS search, and total count."""
        base = self._base_query().where(Task.workspace_id == workspace_id)

        if project_id:
            base = base.where(Task.project_id == project_id)
        if assignee_id:
            base = base.where(Task.assignee_id == assignee_id)
        if status:
            base = base.where(Task.status == status)
        if priority:
            base = base.where(Task.priority == priority)
        if search:
            # PostgreSQL full text search query
            base = base.where(Task.search_vector.op("@@")(func.plainto_tsquery("russian", search)))

        # Count total matches
        count_query = select(func.count()).select_from(base.subquery())
        count_res = await self.session.execute(count_query)
        total = count_res.scalar_one()

        # Fetch page with preloaded relationships
        query = (
            base.options(
                selectinload(Task.labels),
                selectinload(Task.assignee),
                selectinload(Task.creator),
            )
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def would_create_cycle(self, task_id: uuid.UUID, candidate_parent_id: uuid.UUID) -> bool:
        """Check if setting task_id.parent_id = candidate_parent_id would create a circular loop.

        Uses an iterative ancestor check. If task_id is found among candidate_parent_id's ancestors,
        it creates a cycle.
        """
        if task_id == candidate_parent_id:
            return True

        current_id: uuid.UUID | None = candidate_parent_id
        visited: set[uuid.UUID] = {task_id}

        while current_id is not None:
            if current_id in visited:
                return True
            visited.add(current_id)

            query = select(Task.parent_id).where(Task.id == current_id, Task.deleted_at.is_(None))
            res = await self.session.execute(query)
            current_id = res.scalar_one_or_none()

        return False

    async def update_with_optimistic_lock(
        self,
        task_id: uuid.UUID,
        expected_version: int,
        values: dict[str, Any],
    ) -> Task | None:
        """Update task only if version == expected_version, incrementing version by 1.

        Returns updated task or None if version conflict occurred.
        """
        stmt = (
            update(Task)
            .where(
                Task.id == task_id,
                Task.version == expected_version,
                Task.deleted_at.is_(None),
            )
            .values(**values, version=expected_version + 1)
        )
        result = await self.session.execute(stmt)
        if result.rowcount == 0:
            return None

        await self.session.flush()
        return await self.get_with_relations(task_id)
