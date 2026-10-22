"""Milestone and timeline endpoints."""

import uuid

from fastapi import APIRouter, status

from app.api.v1.deps import (
    MilestoneServiceDep,
    RequireMember,
    RequireViewer,
)
from app.schemas.milestone import (
    MilestoneCreate,
    MilestoneRead,
    MilestoneUpdate,
    ProjectTimelineRead,
)

router = APIRouter(
    prefix="/workspaces/{ws_id}/projects/{proj_id}",
    tags=["milestones & timeline"],
)


@router.get("/milestones", response_model=list[MilestoneRead], summary="List project milestones")
async def list_milestones(
    proj_id: uuid.UUID,
    ctx: RequireViewer,
    service: MilestoneServiceDep,
) -> list[MilestoneRead]:
    milestones = await service.list_milestones(ctx.workspace.id, proj_id)
    return [MilestoneRead.model_validate(m) for m in milestones]


@router.post(
    "/milestones",
    response_model=MilestoneRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a milestone (Member+)",
)
async def create_milestone(
    proj_id: uuid.UUID,
    body: MilestoneCreate,
    ctx: RequireMember,
    service: MilestoneServiceDep,
) -> MilestoneRead:
    milestone = await service.create_milestone(ctx.workspace.id, proj_id, body)
    return MilestoneRead.model_validate(milestone)


@router.patch(
    "/milestones/{ms_id}",
    response_model=MilestoneRead,
    summary="Update a milestone (Member+)",
)
async def update_milestone(
    proj_id: uuid.UUID,
    ms_id: uuid.UUID,
    body: MilestoneUpdate,
    ctx: RequireMember,
    service: MilestoneServiceDep,
) -> MilestoneRead:
    milestone = await service.update_milestone(ctx.workspace.id, proj_id, ms_id, body)
    return MilestoneRead.model_validate(milestone)


@router.delete(
    "/milestones/{ms_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a milestone (Member+)",
)
async def delete_milestone(
    proj_id: uuid.UUID,
    ms_id: uuid.UUID,
    ctx: RequireMember,
    service: MilestoneServiceDep,
) -> None:
    await service.delete_milestone(ctx.workspace.id, proj_id, ms_id)


@router.get(
    "/timeline",
    response_model=ProjectTimelineRead,
    summary="Get project timeline for Gantt chart (Viewer+)",
)
async def get_timeline(
    proj_id: uuid.UUID,
    ctx: RequireViewer,
    service: MilestoneServiceDep,
) -> ProjectTimelineRead:
    return await service.get_project_timeline(ctx.workspace.id, proj_id)
