"""Workspace and membership management endpoints."""

import uuid

from fastapi import APIRouter, status

from app.api.v1.deps import (
    CurrentUser,
    RequireAdmin,
    RequireOwner,
    RequireViewer,
    WorkspaceServiceDep,
)
from app.schemas.auth import UserPublic
from app.schemas.workspace import (
    MemberInviteRequest,
    MemberUpdateRoleRequest,
    WorkspaceCreate,
    WorkspaceMemberRead,
    WorkspaceRead,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceRead], summary="List my workspaces")
async def list_workspaces(
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> list[WorkspaceRead]:
    workspaces = await service.list_user_workspaces(current_user.id)
    return [WorkspaceRead.model_validate(w) for w in workspaces]


@router.post(
    "",
    response_model=WorkspaceRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
)
async def create_workspace(
    body: WorkspaceCreate,
    current_user: CurrentUser,
    service: WorkspaceServiceDep,
) -> WorkspaceRead:
    ws = await service.create_workspace(current_user, body)
    return WorkspaceRead.model_validate(ws)


@router.get(
    "/{ws_id}",
    response_model=WorkspaceRead,
    summary="Get workspace details",
)
async def get_workspace(
    ctx: RequireViewer,
) -> WorkspaceRead:
    return WorkspaceRead.model_validate(ctx.workspace)


@router.patch(
    "/{ws_id}",
    response_model=WorkspaceRead,
    summary="Update workspace details (Admin or Owner)",
)
async def update_workspace(
    body: WorkspaceUpdate,
    ctx: RequireAdmin,
    service: WorkspaceServiceDep,
) -> WorkspaceRead:
    ws = await service.update_workspace(ctx.workspace.id, body)
    return WorkspaceRead.model_validate(ws)


@router.delete(
    "/{ws_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete workspace (Owner only)",
)
async def delete_workspace(
    ctx: RequireOwner,
    service: WorkspaceServiceDep,
) -> None:
    await service.delete_workspace(ctx.workspace.id)


# ── Members ───────────────────────────────────────────────────────────────────


@router.get(
    "/{ws_id}/members",
    response_model=list[WorkspaceMemberRead],
    summary="List workspace members",
)
async def list_members(
    ctx: RequireViewer,
    service: WorkspaceServiceDep,
) -> list[WorkspaceMemberRead]:
    members = await service.list_members(ctx.workspace.id)
    return [
        WorkspaceMemberRead(
            id=m.id,
            workspace_id=m.workspace_id,
            user_id=m.user_id,
            role=m.role,  # type: ignore[arg-type]
            status=m.status,  # type: ignore[arg-type]
            joined_at=m.joined_at,
            created_at=m.created_at,
            updated_at=m.updated_at,
            user=UserPublic.model_validate(m.user) if m.user else None,
        )
        for m in members
    ]


@router.post(
    "/{ws_id}/members",
    response_model=WorkspaceMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Invite or add a member (Admin or Owner)",
)
async def invite_member(
    body: MemberInviteRequest,
    ctx: RequireAdmin,
    service: WorkspaceServiceDep,
) -> WorkspaceMemberRead:
    member = await service.invite_member(ctx.workspace.id, body)
    return WorkspaceMemberRead.model_validate(member)


@router.patch(
    "/{ws_id}/members/{user_id}",
    response_model=WorkspaceMemberRead,
    summary="Change member role (Admin or Owner)",
)
async def update_member_role(
    user_id: uuid.UUID,
    body: MemberUpdateRoleRequest,
    ctx: RequireAdmin,
    service: WorkspaceServiceDep,
) -> WorkspaceMemberRead:
    member = await service.update_member_role(ctx.workspace.id, user_id, body)
    return WorkspaceMemberRead.model_validate(member)


@router.delete(
    "/{ws_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member (Admin or Owner)",
)
async def remove_member(
    user_id: uuid.UUID,
    ctx: RequireAdmin,
    service: WorkspaceServiceDep,
) -> None:
    await service.remove_member(ctx.workspace.id, user_id)
