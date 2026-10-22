"""Milestone and timeline service."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.models.milestone import Milestone
from app.models.task import Task
from app.repositories.milestone import MilestoneRepository
from app.repositories.project import ProjectRepository
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate, ProjectTimelineRead
from app.schemas.task import TaskRead


class MilestoneService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.milestone_repo = MilestoneRepository(session)
        self.project_repo = ProjectRepository(session)

    async def create_milestone(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        data: MilestoneCreate,
    ) -> Milestone:
        project = await self.project_repo.get(project_id)
        if not project or project.workspace_id != workspace_id:
            raise NotFoundError("Project not found in this workspace.")

        return await self.milestone_repo.create(
            project_id=project_id,
            title=data.title,
            description=data.description,
            due_date=data.due_date,
            status=data.status,
        )

    async def update_milestone(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        milestone_id: uuid.UUID,
        data: MilestoneUpdate,
    ) -> Milestone:
        ms = await self.milestone_repo.get(milestone_id)
        if not ms or ms.project_id != project_id:
            raise NotFoundError("Milestone not found.")

        updates = data.model_dump(exclude_unset=True)
        return await self.milestone_repo.update(ms, **updates)

    async def delete_milestone(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        milestone_id: uuid.UUID,
    ) -> None:
        ms = await self.milestone_repo.get(milestone_id)
        if not ms or ms.project_id != project_id:
            raise NotFoundError("Milestone not found.")
        await self.milestone_repo.delete(ms)

    async def list_milestones(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[Milestone]:
        project = await self.project_repo.get(project_id)
        if not project or project.workspace_id != workspace_id:
            raise NotFoundError("Project not found.")
        return await self.milestone_repo.list_by_project(project_id)

    async def get_project_timeline(
        self, workspace_id: uuid.UUID, project_id: uuid.UUID
    ) -> ProjectTimelineRead:
        """Fetch all milestones and scheduled tasks with start/due dates for timeline rendering."""
        project = await self.project_repo.get(project_id)
        if not project or project.workspace_id != workspace_id:
            raise NotFoundError("Project not found.")

        milestones = await self.milestone_repo.list_by_project(project_id)

        # Fetch tasks in this project that have at least one timeline date
        task_query = (
            select(Task)
            .where(
                Task.project_id == project_id,
                Task.deleted_at.is_(None),
                (Task.start_date.is_not(None) | Task.due_date.is_not(None)),
            )
            .options(
                selectinload(Task.labels),
                selectinload(Task.assignee),
                selectinload(Task.creator),
            )
            .order_by(Task.start_date.asc().nulls_last(), Task.due_date.asc().nulls_last())
        )
        task_res = await self.session.execute(task_query)
        tasks = list(task_res.scalars().all())

        return ProjectTimelineRead(
            project_id=project_id,
            milestones=milestones,  # type: ignore[arg-type]
            tasks=[TaskRead.model_validate(t) for t in tasks],
        )
