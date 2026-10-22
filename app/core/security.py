"""JWT creation/verification and password hashing (argon2).

Design decisions:
- Access token: HS256 JWT, short TTL (15 min). Stateless, verified by signature.
- Refresh token: opaque bytes (secrets.token_urlsafe), stored hashed in DB/Redis.
  On use → old token invalidated (rotation), new pair issued.
- Blacklist: revoked JTIs stored in Redis with TTL = remaining access token lifetime.
  Checked on every authenticated request.
- argon2 chosen over bcrypt: higher memory hardness, better against GPU attacks.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.core.config import settings

# ── Password hashing ──────────────────────────────────────────────────────────

_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65_536,  # 64 MB – safe on 8 GB laptop
    parallelism=2,
)


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError):
        return False


def password_needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


# ── JWT (access tokens) ───────────────────────────────────────────────────────


def create_access_token(
    user_id: uuid.UUID,
    extra: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    """
    Returns (encoded_jwt, jti, expires_at).
    jti is stored in Redis blacklist on logout.
    """
    jti = str(uuid.uuid4())
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "jti": jti,
        "iat": now,
        "exp": expires_at,
        "type": "access",
        **(extra or {}),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT. Raises jwt.* exceptions on failure.
    Callers translate these to domain errors.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "jti", "exp", "type"]},
    )


# ── Refresh tokens ────────────────────────────────────────────────────────────


def generate_refresh_token() -> str:
    """Generate a cryptographically secure opaque token (URL-safe, 43 chars)."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hash stored in DB/Redis — plain token never persisted."""
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_token_expires_at() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
