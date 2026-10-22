"""Workspace, Membership, and RBAC schemas."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field

from app.schemas.auth import UserPublic
from app.schemas.base import AppBaseModel, TimestampSchema

WorkspaceRole = Literal["owner", "admin", "member", "viewer"]
MemberStatus = Literal["active", "pending", "removed"]


# ── Workspace schemas ─────────────────────────────────────────────────────────


class WorkspaceCreate(AppBaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str | None = Field(default=None, max_length=1000)


class WorkspaceUpdate(AppBaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class WorkspaceRead(TimestampSchema):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    owner_id: uuid.UUID


# ── WorkspaceMember schemas ───────────────────────────────────────────────────


class MemberInviteRequest(AppBaseModel):
    email: EmailStr
    role: WorkspaceRole = "member"


class MemberUpdateRoleRequest(AppBaseModel):
    role: WorkspaceRole


class WorkspaceMemberRead(TimestampSchema):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: WorkspaceRole
    status: MemberStatus
    joined_at: datetime | None
    user: UserPublic | None = None
