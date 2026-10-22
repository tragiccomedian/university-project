"""Authentication endpoints.

All routes are under /api/v1/auth and apply the stricter auth_rate_limit.
"""


from fastapi import APIRouter, Depends, Request, status

from app.api.v1.deps import (
    AuthServiceDep,
    CurrentUser,
    TokenMetaDep,
    auth_rate_limit,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserPublic,
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    dependencies=[Depends(auth_rate_limit)],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        409: {"description": "Email or username already taken"},
        422: {"description": "Validation error (weak password, invalid email, etc.)"},
    },
)
async def register(
    body: RegisterRequest,
    request: Request,
    auth: AuthServiceDep,
) -> RegisterResponse:
    ip = request.client.host if request.client else None
    user, access_token, refresh_token, expires_at = await auth.register(body, ip=ip)
    return RegisterResponse(
        user=UserPublic.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and obtain token pair",
    responses={
        401: {"description": "Invalid credentials"},
        429: {"description": "Too many login attempts"},
    },
)
async def login(
    body: LoginRequest,
    request: Request,
    auth: AuthServiceDep,
) -> TokenResponse:
    ip = request.client.host if request.client else None
    user, access_token, refresh_token, expires_at = await auth.login(body, ip=ip)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        user=UserPublic.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using a refresh token",
    responses={
        401: {"description": "Token invalid, expired, or revoked"},
    },
)
async def refresh(
    body: RefreshRequest,
    auth: AuthServiceDep,
) -> TokenResponse:
    user, access_token, new_refresh, expires_at = await auth.refresh(body.refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        expires_at=expires_at,
        user=UserPublic.model_validate(user),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from the current device",
    description="Revokes the refresh token and blacklists the current access token.",
)
async def logout(
    body: LogoutRequest,
    token_meta: TokenMetaDep,
    auth: AuthServiceDep,
) -> None:
    await auth.logout(
        raw_refresh_token=body.refresh_token,
        access_jti=token_meta.jti,
        access_expires_at=token_meta.expires_at,
    )


@router.delete(
    "/sessions",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from ALL devices",
    description="Revokes all refresh tokens and blacklists the current access token.",
)
async def logout_all(
    current_user: CurrentUser,
    token_meta: TokenMetaDep,
    auth: AuthServiceDep,
) -> None:
    await auth.logout_all(
        user_id=current_user.id,
        access_jti=token_meta.jti,
        access_expires_at=token_meta.expires_at,
    )


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Get current user profile",
)
async def get_me(current_user: CurrentUser) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.put(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description="Verifies old password, updates hash, revokes all sessions.",
    responses={
        403: {"description": "Old password is incorrect"},
    },
)
async def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser,
    token_meta: TokenMetaDep,
    auth: AuthServiceDep,
) -> None:
    await auth.change_password(
        user=current_user,
        data=body,
        access_jti=token_meta.jti,
        access_expires_at=token_meta.expires_at,
    )
