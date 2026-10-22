"""Task business logic service with optimistic locking and validation."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    CyclicDependencyError,
    NotFoundError,
    ValidationError,
    VersionConflictError,
)
from app.models.activity_log import ActivityLog
from app.models.task import Task
from app.models.user import User
from app.repositories.label import LabelRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.workspace import WorkspaceMemberRepository
from app.schemas.task import TaskCreate, TaskFilterParams, TaskUpdate


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.task_repo = TaskRepository(session)
        self.project_repo = ProjectRepository(session)
        self.member_repo = WorkspaceMemberRepository(session)
        self.label_repo = LabelRepository(session)

    async def _validate_assignee(
        self, workspace_id: uuid.UUID, assignee_id: uuid.UUID | None
    ) -> None:
        if assignee_id is not None:
            membership = await self.member_repo.get_membership(workspace_id, assignee_id)
            if not membership or membership.status != "active":
                raise ValidationError("Assignee must be an active member of this workspace.")

    async def create_task(
        self,
        workspace_id: uuid.UUID,
        creator: User,
        data: TaskCreate,
    ) -> Task:
        # 1. Validate project belongs to workspace
        project = await self.project_repo.get(data.project_id)
        if not project or project.workspace_id != workspace_id:
            raise NotFoundError("Project not found in this workspace.")

        # 2. Validate assignee
        await self._validate_assignee(workspace_id, data.assignee_id)

        # 3. Validate parent task
        if data.parent_id:
            parent = await self.task_repo.get(data.parent_id)
            if not parent or parent.workspace_id != workspace_id:
                raise NotFoundError("Parent task not found in this workspace.")

        # 4. Create task
        task = await self.task_repo.create(
            workspace_id=workspace_id,
            project_id=data.project_id,
            creator_id=creator.id,
            assignee_id=data.assignee_id,
            parent_id=data.parent_id,
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            start_date=data.start_date,
            due_date=data.due_date,
            version=1,
        )

        # 5. Attach labels
        if data.label_ids:
            for lid in data.label_ids:
                lbl = await self.label_repo.get(lid)
                if lbl and lbl.workspace_id == workspace_id:
                    task.labels.append(lbl)
            await self.session.flush()

        # 6. Audit log
        self.session.add(
            ActivityLog(
                actor_id=creator.id,
                action="create",
                entity_type="task",
                entity_id=task.id,
                workspace_id=workspace_id,
                diff={"title": [None, task.title], "status": [None, task.status]},
            )
        )
        await self.session.flush()

        return await self.task_repo.get_with_relations(task.id)  # type: ignore[return-value]

    async def get_task(self, workspace_id: uuid.UUID, task_id: uuid.UUID) -> Task:
        task = await self.task_repo.get_with_relations(task_id)
        if not task or task.workspace_id != workspace_id:
            raise NotFoundError("Task not found.")
        return task

    async def update_task(
        self,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        actor: User,
        data: TaskUpdate,
    ) -> Task:
        task = await self.get_task(workspace_id, task_id)

        # 1. Optimistic locking version check
        if task.version != data.version:
            raise VersionConflictError(
                f"Task was modified concurrently. Current version is {task.version}, but {data.version} was provided."
            )

        # 2. Circular subtask dependency check
        if data.parent_id is not None:
            if await self.task_repo.would_create_cycle(task_id, data.parent_id):
                raise CyclicDependencyError(
                    "Setting this parent task would create a cyclic dependency."
                )
            parent = await self.task_repo.get(data.parent_id)
            if not parent or parent.workspace_id != workspace_id:
                raise NotFoundError("Parent task not found.")

        # 3. Validate assignee
        if data.assignee_id is not None:
            await self._validate_assignee(workspace_id, data.assignee_id)

        # 4. Prepare updates and track audit diff
        updates = data.model_dump(exclude={"version"}, exclude_unset=True)
        diff: dict[str, Any] = {}
        for k, v in updates.items():
            old_val = getattr(task, k)
            if old_val != v:
                diff[k] = [str(old_val), str(v)]

        # 5. Apply optimistic lock update
        updated_task = await self.task_repo.update_with_optimistic_lock(
            task_id=task_id,
            expected_version=data.version,
            values=updates,
        )
        if not updated_task:
            raise VersionConflictError("Concurrent update conflict detected. Please retry.")

        # 6. Audit log if changes occurred
        if diff:
            self.session.add(
                ActivityLog(
                    actor_id=actor.id,
                    action="update",
                    entity_type="task",
                    entity_id=task_id,
                    workspace_id=workspace_id,
                    diff=diff,
                )
            )
            await self.session.flush()

        return updated_task

    async def delete_task(self, workspace_id: uuid.UUID, task_id: uuid.UUID, actor: User) -> None:
        task = await self.get_task(workspace_id, task_id)
        await self.task_repo.soft_delete(task)

        self.session.add(
            ActivityLog(
                actor_id=actor.id,
                action="delete",
                entity_type="task",
                entity_id=task_id,
                workspace_id=workspace_id,
            )
        )
        await self.session.flush()

    async def list_tasks(
        self, workspace_id: uuid.UUID, params: TaskFilterParams
    ) -> tuple[list[Task], int]:
        return await self.task_repo.list_tasks(
            workspace_id=workspace_id,
            project_id=params.project_id,
            assignee_id=params.assignee_id,
            status=params.status,
            priority=params.priority,
            search=params.search,
            limit=params.limit,
            offset=params.offset,
        )

    async def add_label_to_task(
        self, workspace_id: uuid.UUID, task_id: uuid.UUID, label_id: uuid.UUID
    ) -> Task:
        task = await self.get_task(workspace_id, task_id)
        lbl = await self.label_repo.get(label_id)
        if not lbl or lbl.workspace_id != workspace_id:
            raise NotFoundError("Label not found.")

        if lbl not in task.labels:
            task.labels.append(lbl)
            await self.session.flush()

        return await self.task_repo.get_with_relations(task_id)  # type: ignore[return-value]

    async def remove_label_from_task(
        self, workspace_id: uuid.UUID, task_id: uuid.UUID, label_id: uuid.UUID
    ) -> Task:
        task = await self.get_task(workspace_id, task_id)
        lbl = await self.label_repo.get(label_id)
        if not lbl or lbl.workspace_id != workspace_id:
            raise NotFoundError("Label not found.")

        if lbl in task.labels:
            task.labels.remove(lbl)
            await self.session.flush()

        return await self.task_repo.get_with_relations(task_id)  # type: ignore[return-value]
