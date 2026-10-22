"""Comment service with @mention notification creation."""

import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, PermissionDeniedError
from app.models.activity_log import ActivityLog
from app.models.comment import Comment
from app.models.notification import Notification
from app.models.user import User
from app.repositories.comment import CommentRepository
from app.repositories.task import TaskRepository
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceMemberRepository
from app.schemas.comment import CommentCreate, CommentUpdate


class CommentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.comment_repo = CommentRepository(session)
        self.task_repo = TaskRepository(session)
        self.user_repo = UserRepository(session)
        self.member_repo = WorkspaceMemberRepository(session)

    async def create_comment(
        self,
        workspace_id: uuid.UUID,
        task_id: uuid.UUID,
        author: User,
        data: CommentCreate,
    ) -> Comment:
        task = await self.task_repo.get(task_id)
        if not task or task.workspace_id != workspace_id:
            raise NotFoundError("Task not found.")

        comment = await self.comment_repo.create(
            task_id=task_id,
            author_id=author.id,
            content=data.content,
        )

        # Parse @mentions (e.g. @alice, @bob_dev)
        mentions = set(re.findall(r"@([a-zA-Z0-9_-]+)", data.content))
        for username in mentions:
            user = await self.user_repo.get_by_username(username)
            if user and user.id != author.id:
                # Check if mentioned user is a member of this workspace
                membership = await self.member_repo.get_membership(workspace_id, user.id)
                if membership and membership.status == "active":
                    self.session.add(
                        Notification(
                            recipient_id=user.id,
                            actor_id=author.id,
                            type="MENTION",
                            entity_type="task",
                            entity_id=task_id,
                            payload={
                                "message": f"{author.display_name} mentioned you in a comment on '{task.title}'",
                                "comment_id": str(comment.id),
                            },
                        )
                    )

        # Audit log
        self.session.add(
            ActivityLog(
                actor_id=author.id,
                action="create",
                entity_type="comment",
                entity_id=comment.id,
                workspace_id=workspace_id,
            )
        )
        await self.session.flush()

        return await self.comment_repo.get_with_author(comment.id)  # type: ignore[return-value]

    async def update_comment(
        self,
        workspace_id: uuid.UUID,
        comment_id: uuid.UUID,
        author: User,
        data: CommentUpdate,
    ) -> Comment:
        comment = await self.comment_repo.get(comment_id)
        if not comment:
            raise NotFoundError("Comment not found.")
        if comment.author_id != author.id:
            raise PermissionDeniedError("You can only edit your own comments.")

        updated = await self.comment_repo.update(comment, content=data.content)
        return await self.comment_repo.get_with_author(updated.id)  # type: ignore[return-value]

    async def delete_comment(
        self,
        workspace_id: uuid.UUID,
        comment_id: uuid.UUID,
        actor: User,
        user_role: str,
    ) -> None:
        comment = await self.comment_repo.get(comment_id)
        if not comment:
            raise NotFoundError("Comment not found.")

        # Authors can delete their own; Admin and Owner can delete any comment
        if comment.author_id != actor.id and user_role not in ("admin", "owner"):
            raise PermissionDeniedError("You do not have permission to delete this comment.")

        await self.comment_repo.soft_delete(comment)

    async def list_comments(self, workspace_id: uuid.UUID, task_id: uuid.UUID) -> list[Comment]:
        task = await self.task_repo.get(task_id)
        if not task or task.workspace_id != workspace_id:
            raise NotFoundError("Task not found.")
        return await self.comment_repo.list_by_task(task_id)
