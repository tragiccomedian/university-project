import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_valid_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Return token only if it exists and has not expired."""
        rt = await self.get_by_hash(token_hash)
        if rt is None:
            return None
        if rt.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            return None
        return rt

    async def delete_by_user(self, user_id: uuid.UUID) -> None:
        """Delete ALL refresh tokens for a user (logout from all devices)."""
        await self.session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        await self.session.flush()

    async def delete_expired(self) -> int:
        """Remove expired tokens. Called by cleanup worker."""
        result = await self.session.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.now(UTC))
        )
        await self.session.flush()
        return result.rowcount  # type: ignore[return-value]
