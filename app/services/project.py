"""Project business logic service."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProjectRepository(session)

    async def create_project(self, workspace_id: uuid.UUID, data: ProjectCreate) -> Project:
        return await self.repo.create(
            workspace_id=workspace_id,
            name=data.name,
            description=data.description,
            color=data.color,
            start_date=data.start_date,
            end_date=data.end_date,
            status="active",
        )

    async def get_project(self, workspace_id: uuid.UUID, project_id: uuid.UUID) -> Project:
        project = await self.repo.get(project_id)
        if not project or project.workspace_id != workspace_id:
            raise NotFoundError("Project not found.")
        return project

    async def update_project(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ProjectUpdate,
    ) -> Project:
        project = await self.get_project(workspace_id, project_id)
        updates = data.model_dump(exclude_unset=True)
        return await self.repo.update(project, **updates)

    async def delete_project(self, workspace_id: uuid.UUID, project_id: uuid.UUID) -> None:
        project = await self.get_project(workspace_id, project_id)
        await self.repo.soft_delete(project)

    async def list_projects(
        self, workspace_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> tuple[list[Project], int]:
        items = await self.repo.list_by_workspace(workspace_id, limit=limit, offset=offset)
        total = await self.repo.count_by_workspace(workspace_id)
        return items, total
