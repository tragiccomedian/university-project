"""Workspace and membership management service."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, LastOwnerError, NotFoundError
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceMemberRepository, WorkspaceRepository
from app.schemas.workspace import (
    MemberInviteRequest,
    MemberUpdateRoleRequest,
    WorkspaceCreate,
    WorkspaceUpdate,
)


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ws_repo = WorkspaceRepository(session)
        self.member_repo = WorkspaceMemberRepository(session)
        self.user_repo = UserRepository(session)

    async def create_workspace(self, user: User, data: WorkspaceCreate) -> Workspace:
        """Create workspace and assign user as the initial Owner."""
        if await self.ws_repo.get_by_slug(data.slug):
            raise ConflictError("A workspace with this slug already exists.")

        workspace = await self.ws_repo.create(
            name=data.name,
            slug=data.slug,
            description=data.description,
            owner_id=user.id,
        )

        # Creator automatically becomes the Owner member
        await self.member_repo.create(
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
            status="active",
            joined_at=datetime.now(UTC),
        )
        return workspace

    async def get_workspace(self, workspace_id: uuid.UUID) -> Workspace:
        ws = await self.ws_repo.get(workspace_id)
        if not ws:
            raise NotFoundError("Workspace not found.")
        return ws

    async def update_workspace(self, workspace_id: uuid.UUID, data: WorkspaceUpdate) -> Workspace:
        ws = await self.get_workspace(workspace_id)
        updates = data.model_dump(exclude_unset=True)
        return await self.ws_repo.update(ws, **updates)

    async def delete_workspace(self, workspace_id: uuid.UUID) -> None:
        ws = await self.get_workspace(workspace_id)
        await self.ws_repo.soft_delete(ws)

    async def list_user_workspaces(self, user_id: uuid.UUID) -> list[Workspace]:
        return await self.ws_repo.list_for_user(user_id)

    # ── Members Management ────────────────────────────────────────────────────

    async def invite_member(
        self, workspace_id: uuid.UUID, data: MemberInviteRequest
    ) -> WorkspaceMember:
        ws = await self.get_workspace(workspace_id)
        user = await self.user_repo.get_by_email(data.email)
        if not user:
            raise NotFoundError(f"User with email '{data.email}' was not found.")

        existing = await self.member_repo.get_membership(ws.id, user.id)
        if existing and existing.status in ("active", "pending"):
            raise ConflictError("User is already a member of this workspace.")

        if existing and existing.status == "removed":
            # Re-activate
            return await self.member_repo.update(
                existing,
                role=data.role,
                status="active",
                joined_at=datetime.now(UTC),
            )

        return await self.member_repo.create(
            workspace_id=ws.id,
            user_id=user.id,
            role=data.role,
            status="active",
            joined_at=datetime.now(UTC),
        )

    async def update_member_role(
        self,
        workspace_id: uuid.UUID,
        target_user_id: uuid.UUID,
        data: MemberUpdateRoleRequest,
    ) -> WorkspaceMember:
        membership = await self.member_repo.get_membership(workspace_id, target_user_id)
        if not membership or membership.status != "active":
            raise NotFoundError("Member not found in this workspace.")

        # If demoting an owner, ensure there is at least one other active owner
        if membership.role == "owner" and data.role != "owner":
            active_owners = await self.member_repo.count_active_owners(workspace_id)
            if active_owners <= 1:
                raise LastOwnerError()

        return await self.member_repo.update(membership, role=data.role)

    async def remove_member(self, workspace_id: uuid.UUID, target_user_id: uuid.UUID) -> None:
        membership = await self.member_repo.get_membership(workspace_id, target_user_id)
        if not membership or membership.status != "active":
            raise NotFoundError("Member not found in this workspace.")

        if membership.role == "owner":
            active_owners = await self.member_repo.count_active_owners(workspace_id)
            if active_owners <= 1:
                raise LastOwnerError()

        await self.member_repo.update(membership, status="removed")

    async def list_members(self, workspace_id: uuid.UUID) -> list[WorkspaceMember]:
        await self.get_workspace(workspace_id)
        return await self.member_repo.list_members(workspace_id)
