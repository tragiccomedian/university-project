import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hashing() -> None:
    """Argon2 password hash creation and verification."""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_jwt_access_token() -> None:
    """JWT access token encodes sub, jti, exp, and decodes properly."""
    user_id = uuid.uuid4()
    token, jti, expires_at = create_access_token(user_id)

    assert isinstance(token, str)
    assert isinstance(jti, str)
    assert expires_at > datetime.now(UTC)

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["jti"] == jti
    assert payload["type"] == "access"


def test_refresh_token_generation_and_hashing() -> None:
    """Opaque refresh tokens and SHA-256 digests."""
    raw1 = generate_refresh_token()
    raw2 = generate_refresh_token()
    assert raw1 != raw2
    assert len(raw1) >= 40

    hash1 = hash_refresh_token(raw1)
    hash2 = hash_refresh_token(raw1)
    assert hash1 == hash2  # Deterministic SHA-256
    assert len(hash1) == 64


@pytest.mark.asyncio
async def test_register_validation_password_no_digit(client: AsyncClient) -> None:
    """Registration with no digits in password must fail with 422."""
    payload = {
        "email": "test@example.com",
        "username": "valid_user",
        "password": "PasswordWithoutDigits",
        "display_name": "Test User",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_register_validation_password_no_uppercase(client: AsyncClient) -> None:
    """Registration with no uppercase in password must fail with 422."""
    payload = {
        "email": "test@example.com",
        "username": "valid_user",
        "password": "passwordwith1234",
        "display_name": "Test User",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_register_validation_invalid_email(client: AsyncClient) -> None:
    """Registration with invalid email format must fail with 422."""
    payload = {
        "email": "not-an-email",
        "username": "valid_user",
        "password": "ValidPassword123",
        "display_name": "Test User",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_invalid_credentials_format(client: AsyncClient) -> None:
    """Unregistered or invalid credentials must return 401."""
    payload = {
        "email": "nonexistent@example.com",
        "password": "WrongPassword123",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "AUTHENTICATION_FAILED"
