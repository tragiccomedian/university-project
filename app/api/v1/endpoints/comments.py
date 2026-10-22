"""Comment endpoints."""

import uuid

from fastapi import APIRouter, status

from app.api.v1.deps import (
    CommentServiceDep,
    RequireMember,
    RequireViewer,
)
from app.schemas.auth import UserPublic
from app.schemas.comment import CommentCreate, CommentRead, CommentUpdate

router = APIRouter(prefix="/workspaces/{ws_id}/tasks/{task_id}/comments", tags=["comments"])


@router.get("", response_model=list[CommentRead], summary="List task comments")
async def list_comments(
    task_id: uuid.UUID,
    ctx: RequireViewer,
    service: CommentServiceDep,
) -> list[CommentRead]:
    comments = await service.list_comments(ctx.workspace.id, task_id)
    return [
        CommentRead(
            id=c.id,
            task_id=c.task_id,
            author_id=c.author_id,
            content=c.content,
            created_at=c.created_at,
            updated_at=c.updated_at,
            author=UserPublic.model_validate(c.author) if c.author else None,
        )
        for c in comments
    ]


@router.post(
    "",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment with optional @mentions (Member+)",
)
async def create_comment(
    task_id: uuid.UUID,
    body: CommentCreate,
    ctx: RequireMember,
    service: CommentServiceDep,
) -> CommentRead:
    comment = await service.create_comment(ctx.workspace.id, task_id, ctx.user, body)
    return CommentRead(
        id=comment.id,
        task_id=comment.task_id,
        author_id=comment.author_id,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author=UserPublic.model_validate(comment.author) if comment.author else None,
    )


@router.patch(
    "/{comment_id}",
    response_model=CommentRead,
    summary="Update own comment",
)
async def update_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    body: CommentUpdate,
    ctx: RequireMember,
    service: CommentServiceDep,
) -> CommentRead:
    comment = await service.update_comment(ctx.workspace.id, comment_id, ctx.user, body)
    return CommentRead(
        id=comment.id,
        task_id=comment.task_id,
        author_id=comment.author_id,
        content=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author=UserPublic.model_validate(comment.author) if comment.author else None,
    )


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment (Author or Admin/Owner)",
)
async def delete_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    ctx: RequireMember,
    service: CommentServiceDep,
) -> None:
    await service.delete_comment(ctx.workspace.id, comment_id, ctx.user, ctx.role)
