from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_db)):
    service = AuthService(session)
    user = await service.register(email=payload.email, password=payload.password)
    tokens = await service.login(email=payload.email, password=payload.password)
    _, token_pair = tokens
    return AuthResponse(user=UserRead.model_validate(user), **token_pair.model_dump())


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db)):
    service = AuthService(session)
    user, token_pair = await service.login(email=payload.email, password=payload.password)
    return AuthResponse(user=UserRead.model_validate(user), **token_pair.model_dump())


@router.post("/refresh", response_model=None)
async def refresh(payload: RefreshRequest, session: AsyncSession = Depends(get_db)):
    service = AuthService(session)
    token_pair = await service.refresh(raw_refresh_token=payload.refresh_token)
    return token_pair


@router.post("/logout", response_model=MessageResponse)
async def logout(payload: LogoutRequest, session: AsyncSession = Depends(get_db)):
    service = AuthService(session)
    await service.logout(raw_refresh_token=payload.refresh_token)
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return UserRead.model_validate(current_user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(payload: ForgotPasswordRequest, session: AsyncSession = Depends(get_db)):
    service = AuthService(session)
    await service.forgot_password(email=payload.email)
    return MessageResponse(
        message="If an account exists for this email, a password reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(payload: ResetPasswordRequest, session: AsyncSession = Depends(get_db)):
    service = AuthService(session)
    await service.reset_password(raw_token=payload.token, new_password=payload.new_password)
    return MessageResponse(message="Password has been reset successfully.")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(payload: VerifyEmailRequest, session: AsyncSession = Depends(get_db)):
    service = AuthService(session)
    await service.verify_email(raw_token=payload.token)
    return MessageResponse(message="Email verified successfully.")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Changes the current user's password after verifying their current
    one, and revokes every other session's refresh tokens so other
    logged-in devices/browsers must re-authenticate."""
    service = AuthService(session)
    await service.change_password(
        user_id=current_user.id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return MessageResponse(message="Password changed successfully.")
