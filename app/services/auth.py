"""Authentication business logic.

Flow summary:
  register  → create User + default NotificationSettings + issue token pair
  login     → verify password + issue token pair
  refresh   → validate refresh token (DB + Redis) → rotate → issue new pair
  logout    → delete refresh token + blacklist jti in Redis
  logout_all→ delete ALL user refresh tokens + blacklist current jti
  change_pw → verify old password → rehash → rotate ALL tokens
"""

import uuid
from datetime import UTC, datetime

import jwt
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import (
    AuthenticationError,
    ConflictError,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_password,
)
from app.models.notification_setting import NotificationSetting
from app.models.user import User
from app.repositories.token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
)

# Redis key helpers
_BLACKLIST_PREFIX = "blacklist:"
_RT_PREFIX = "rt:"


def _blacklist_key(jti: str) -> str:
    return f"{_BLACKLIST_PREFIX}{jti}"


def _rt_redis_key(token_hash: str) -> str:
    return f"{_RT_PREFIX}{token_hash}"


class AuthService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis) -> None:
        self.session = session
        self.redis = redis
        self.user_repo = UserRepository(session)
        self.token_repo = RefreshTokenRepository(session)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _issue_token_pair(
        self, user: User, device_name: str | None, ip: str | None
    ) -> tuple[str, str, datetime]:
        """Create access + refresh token, persist refresh in DB + Redis."""
        access_token, jti, expires_at = create_access_token(user.id)

        raw_refresh = generate_refresh_token()
        rt_hash = hash_refresh_token(raw_refresh)
        rt_expires = refresh_token_expires_at()

        # Persist in DB
        await self.token_repo.create(
            user_id=user.id,
            token_hash=rt_hash,
            device_name=device_name,
            ip_address=ip,
            expires_at=rt_expires,
        )

        # Cache in Redis for fast lookup (TTL = refresh token lifetime in seconds)
        ttl = settings.refresh_token_expire_seconds
        await self.redis.setex(_rt_redis_key(rt_hash), ttl, str(user.id))

        return access_token, raw_refresh, expires_at

    async def _blacklist_jti(self, jti: str, expires_at: datetime) -> None:
        """Add jti to Redis blacklist until access token naturally expires."""
        remaining = int((expires_at - datetime.now(UTC)).total_seconds())
        if remaining > 0:
            await self.redis.setex(_blacklist_key(jti), remaining, "1")

    async def _is_jti_blacklisted(self, jti: str) -> bool:
        return await self.redis.exists(_blacklist_key(jti)) == 1  # type: ignore[return-value]

    # ── Public API ────────────────────────────────────────────────────────────

    async def register(
        self, data: RegisterRequest, ip: str | None = None
    ) -> tuple[User, str, str, datetime]:
        """Register a new user. Returns (user, access_token, refresh_token, expires_at)."""
        email = data.email.lower()

        if await self.user_repo.email_exists(email):
            raise ConflictError("A user with this email already exists.")
        if await self.user_repo.username_exists(data.username):
            raise ConflictError("This username is already taken.")

        user = await self.user_repo.create(
            email=email,
            username=data.username,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
        )

        # Create default notification settings for all channels
        for channel in ("in_app", "email", "telegram"):
            self.session.add(
                NotificationSetting(
                    user_id=user.id,
                    channel=channel,
                    is_enabled=(channel == "in_app"),  # only in_app on by default
                )
            )

        access_token, refresh_token, expires_at = await self._issue_token_pair(
            user, device_name=None, ip=ip
        )
        return user, access_token, refresh_token, expires_at

    async def login(
        self, data: LoginRequest, ip: str | None = None
    ) -> tuple[User, str, str, datetime]:
        """Authenticate and issue token pair."""
        user = await self.user_repo.get_by_email(data.email.lower())
        # Constant-time: always call verify even if user is None (fake hash)
        _fake = "$argon2id$v=19$m=65536,t=2,p=2$fake$fake"
        valid = verify_password(data.password, user.password_hash if user else _fake)

        if not user or not valid or not user.is_active:
            # Return same error for all cases — don't reveal which part failed
            raise AuthenticationError("Invalid email or password.")

        access_token, refresh_token, expires_at = await self._issue_token_pair(
            user, device_name=data.device_name, ip=ip
        )
        return user, access_token, refresh_token, expires_at

    async def refresh(self, raw_refresh_token: str) -> tuple[User, str, str, datetime]:
        """Validate refresh token → rotate → return new pair."""
        rt_hash = hash_refresh_token(raw_refresh_token)

        # Fast path: check Redis first
        cached_uid = await self.redis.get(_rt_redis_key(rt_hash))
        if cached_uid is None:
            # Fall back to DB (handles Redis eviction / restart)
            db_token = await self.token_repo.get_valid_by_hash(rt_hash)
            if db_token is None:
                raise TokenRevokedError()
            user_id = db_token.user_id
        else:
            user_id = uuid.UUID(cached_uid)
            # Still verify DB record exists (not expired or manually revoked)
            db_token = await self.token_repo.get_valid_by_hash(rt_hash)
            if db_token is None:
                await self.redis.delete(_rt_redis_key(rt_hash))
                raise TokenRevokedError()

        user = await self.user_repo.get(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User account is inactive.")

        # Rotation: delete old token
        await self.token_repo.delete(db_token)
        await self.redis.delete(_rt_redis_key(rt_hash))

        # Issue new pair
        access_token, new_refresh, expires_at = await self._issue_token_pair(
            user, device_name=db_token.device_name, ip=db_token.ip_address
        )
        return user, access_token, new_refresh, expires_at

    async def logout(
        self, raw_refresh_token: str, access_jti: str, access_expires_at: datetime
    ) -> None:
        """Revoke single refresh token + blacklist current access token."""
        rt_hash = hash_refresh_token(raw_refresh_token)
        db_token = await self.token_repo.get_by_hash(rt_hash)
        if db_token:
            await self.token_repo.delete(db_token)
            await self.redis.delete(_rt_redis_key(rt_hash))
        # Blacklist jti regardless (idempotent)
        await self._blacklist_jti(access_jti, access_expires_at)

    async def logout_all(
        self, user_id: uuid.UUID, access_jti: str, access_expires_at: datetime
    ) -> None:
        """Revoke ALL refresh tokens for user + blacklist current access token."""
        await self.token_repo.delete_by_user(user_id)
        # Clean Redis keys — pattern scan (acceptable for small token counts)
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=f"{_RT_PREFIX}*", count=100)
            for key in keys:
                uid = await self.redis.get(key)
                if uid == str(user_id):
                    await self.redis.delete(key)
            if cursor == 0:
                break
        await self._blacklist_jti(access_jti, access_expires_at)

    async def change_password(
        self,
        user: User,
        data: ChangePasswordRequest,
        access_jti: str,
        access_expires_at: datetime,
    ) -> None:
        """Verify old password → set new hash → revoke all sessions."""
        if not verify_password(data.old_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect.")
        await self.user_repo.update(user, password_hash=hash_password(data.new_password))
        await self.logout_all(user.id, access_jti, access_expires_at)

    async def verify_access_token(self, token: str) -> dict:
        """Decode and validate access token, checking blacklist."""
        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError:
            raise TokenInvalidError()

        if payload.get("type") != "access":
            raise TokenInvalidError()

        jti = payload.get("jti", "")
        if await self._is_jti_blacklisted(jti):
            raise TokenRevokedError()

        return payload
