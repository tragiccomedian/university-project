"""Base repository with generic typed CRUD helpers."""

import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic async repository.

    Subclass and set `model` class attribute.
    All methods respect soft-delete: they only return rows where
    deleted_at IS NULL (if the model has that column).
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base_query(self):  # type: ignore[no-untyped-def]
        q = select(self.model)
        if hasattr(self.model, "deleted_at"):
            q = q.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        return q

    async def get(self, id: uuid.UUID) -> ModelT | None:
        result = await self.session.execute(
            self._base_query().where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def get_or_none(self, **kwargs: Any) -> ModelT | None:
        q = self._base_query()
        for field, value in kwargs.items():
            q = q.where(getattr(self.model, field) == value)
        result = await self.session.execute(q)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        **filters: Any,
    ) -> list[ModelT]:
        q = self._base_query()
        for field, value in filters.items():
            q = q.where(getattr(self.model, field) == value)
        q = q.limit(limit).offset(offset)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def count(self, **filters: Any) -> int:
        q = select(func.count()).select_from(self.model)
        if hasattr(self.model, "deleted_at"):
            q = q.where(self.model.deleted_at.is_(None))  # type: ignore[attr-defined]
        for field, value in filters.items():
            q = q.where(getattr(self.model, field) == value)
        result = await self.session.execute(q)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, instance: ModelT, **kwargs: Any) -> ModelT:
        for field, value in kwargs.items():
            setattr(instance, field, value)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Hard delete. Use soft_delete() for soft-deletable models."""
        await self.session.delete(instance)
        await self.session.flush()

    async def soft_delete(self, instance: ModelT) -> ModelT:
        """Set deleted_at = now(). Model must have SoftDeleteMixin."""
        return await self.update(instance, deleted_at=datetime.now(UTC))
