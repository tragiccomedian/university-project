import uuid
from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import AppBaseModel

# ── User sub-schema (embedded in auth responses) ──────────────────────────────


class UserPublic(AppBaseModel):
    id: uuid.UUID
    email: str
    username: str
    display_name: str
    avatar_url: str | None
    is_active: bool


# ── Register ──────────────────────────────────────────────────────────────────


class RegisterRequest(AppBaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class RegisterResponse(AppBaseModel):
    user: UserPublic
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime


# ── Login ─────────────────────────────────────────────────────────────────────


class LoginRequest(AppBaseModel):
    email: EmailStr
    password: str
    device_name: str | None = Field(default=None, max_length=255)


class TokenResponse(AppBaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserPublic


# ── Refresh ───────────────────────────────────────────────────────────────────


class RefreshRequest(AppBaseModel):
    refresh_token: str


# ── Logout ────────────────────────────────────────────────────────────────────


class LogoutRequest(AppBaseModel):
    refresh_token: str


# ── Password change ───────────────────────────────────────────────────────────


class ChangePasswordRequest(AppBaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v
