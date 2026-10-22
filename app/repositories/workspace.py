"""Workspace and WorkspaceMember repositories."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    async def get_by_slug(self, slug: str) -> Workspace | None:
        result = await self.session.execute(self._base_query().where(Workspace.slug == slug))
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID) -> list[Workspace]:
        """Return all workspaces where user is an active member."""
        query = (
            self._base_query()
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "active",
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    model = WorkspaceMember

    async def get_membership(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> WorkspaceMember | None:
        query = (
            select(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .options(selectinload(WorkspaceMember.user))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_members(self, workspace_id: uuid.UUID) -> list[WorkspaceMember]:
        query = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .options(selectinload(WorkspaceMember.user))
            .order_by(WorkspaceMember.created_at.asc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_active_owners(self, workspace_id: uuid.UUID) -> int:
        query = (
            select(func.count())
            .select_from(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == "owner",
                WorkspaceMember.status == "active",
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one()
