"""
Business logic for registration, login, token refresh/rotation, logout,
password reset and email verification. Routes call into this service only;
they never touch the ORM or repositories directly.
"""
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationAppError
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password_async,
    refresh_token_expiry,
    verify_dummy_password_async,
    verify_password_async,
)
from app.email.interface import EmailMessage
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.verification_token_repository import (
    EmailVerificationTokenRepository,
    PasswordResetTokenRepository,
)
from app.schemas.auth import TokenPair
from app.services.audit_service import AuditService

_EMAIL_VERIFICATION_TTL = timedelta(hours=48)
_PASSWORD_RESET_TTL = timedelta(hours=1)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.email_verification_tokens = EmailVerificationTokenRepository(session)
        self.password_reset_tokens = PasswordResetTokenRepository(session)
        self.audit = AuditService(session)

    # ------------------------------------------------------------------
    async def register(self, *, email: str, password: str) -> tuple[User, TokenPair]:
        """Creates the account and issues its first token pair directly --
        re-running `login()` here would verify the freshly hashed password
        a second time (a second ~100ms+ Argon2 pass) for no benefit.

        The verification email is NOT sent here; the route schedules
        `send_verification_email` as a background task so a slow mail
        server can't delay the signup response."""
        existing = await self.users.get_by_email(email)
        if existing is not None:
            raise ConflictError("An account with this email already exists.")

        password_hash = await hash_password_async(password)
        user = await self.users.create(
            email=email,
            password_hash=password_hash,
            terms_accepted_at=datetime.now(UTC),
            terms_version=settings.terms_version,
        )
        tokens = await self._issue_token_pair(user.id)
        await self.audit.record(user_id=user.id, event_type="consent_given")
        await self.audit.record(user_id=user.id, event_type="login")
        return user, tokens

    async def build_verification_email(self, user: User) -> EmailMessage:
        """Persists a verification token and returns the email to send. The
        DB write happens inside the request (it needs the request's
        session); actually *delivering* the message is left to the caller
        (see `deliver_email`) so it can run after the response is sent."""
        raw_token = generate_opaque_token()
        await self.email_verification_tokens.create(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=datetime.now(UTC) + _EMAIL_VERIFICATION_TTL,
        )
        verify_url = f"{settings.frontend_base_url}/verify-email?token={raw_token}"
        return EmailMessage(
            to=user.email,
            subject="Verify your CareQuill account",
            html_body=(
                f"<p>Welcome to CareQuill. Please verify your email by visiting:</p>"
                f"<p><a href='{verify_url}'>{verify_url}</a></p>"
                f"<p>This link expires in 48 hours.</p>"
            ),
            text_body=f"Verify your account: {verify_url}",
        )

    async def verify_email(self, *, raw_token: str) -> None:
        token = await self.email_verification_tokens.get_valid_by_hash(hash_opaque_token(raw_token))
        if token is None:
            raise ValidationAppError("This verification link is invalid or has expired.")
        user = await self.users.get_by_id(token.user_id)
        if user is None:
            raise ValidationAppError("This verification link is invalid or has expired.")
        await self.users.mark_verified(user)
        await self.email_verification_tokens.mark_used(token)

    # ------------------------------------------------------------------
    async def login(self, *, email: str, password: str) -> tuple[User, TokenPair]:
        user = await self.users.get_by_email(email)
        if user is None:
            await verify_dummy_password_async(password)
            raise UnauthorizedError("Incorrect email or password.")
        if not await verify_password_async(password, user.password_hash):
            raise UnauthorizedError("Incorrect email or password.")
        if not user.is_active:
            raise UnauthorizedError("This account has been deactivated.")

        tokens = await self._issue_token_pair(user.id)
        await self.audit.record(user_id=user.id, event_type="login")
        return user, tokens

    async def _issue_token_pair(self, user_id: uuid.UUID) -> TokenPair:
        access_token = create_access_token(user_id)
        raw_refresh_token = generate_opaque_token()
        await self.refresh_tokens.create(
            user_id=user_id,
            token_hash=hash_opaque_token(raw_refresh_token),
            expires_at=refresh_token_expiry(),
        )
        return TokenPair(access_token=access_token, refresh_token=raw_refresh_token)

    # ------------------------------------------------------------------
    async def refresh(self, *, raw_refresh_token: str) -> TokenPair:
        """Refresh token rotation: the presented token is revoked and a new
        one issued, whether or not it was valid, its hash is not reused --
        this limits the blast radius of a leaked/replayed refresh token."""
        token_hash = hash_opaque_token(raw_refresh_token)
        stored = await self.refresh_tokens.get_by_hash(token_hash)
        if stored is None or not stored.is_active:
            raise UnauthorizedError("Refresh token is invalid or has expired.")

        await self.refresh_tokens.revoke(stored)
        return await self._issue_token_pair(stored.user_id)

    async def logout(self, *, raw_refresh_token: str) -> None:
        token_hash = hash_opaque_token(raw_refresh_token)
        stored = await self.refresh_tokens.get_by_hash(token_hash)
        if stored is not None and stored.revoked_at is None:
            await self.refresh_tokens.revoke(stored)
            await self.audit.record(user_id=stored.user_id, event_type="logout")

    # ------------------------------------------------------------------
    async def forgot_password(self, *, email: str) -> EmailMessage | None:
        """Returns the reset email to deliver, or None when no such account
        exists. The caller delivers it in the background in both cases, so
        the response time never reveals whether the email is registered."""
        user = await self.users.get_by_email(email)
        if user is None:
            return None
        raw_token = generate_opaque_token()
        await self.password_reset_tokens.create(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=datetime.now(UTC) + _PASSWORD_RESET_TTL,
        )
        reset_url = f"{settings.frontend_base_url}/reset-password?token={raw_token}"
        return EmailMessage(
            to=user.email,
            subject="Reset your CareQuill password",
            html_body=(
                f"<p>We received a request to reset your password. Visit:</p>"
                f"<p><a href='{reset_url}'>{reset_url}</a></p>"
                f"<p>This link expires in 1 hour. If you did not request this, "
                f"you can safely ignore this email.</p>"
            ),
            text_body=f"Reset your password: {reset_url}",
        )

    async def reset_password(self, *, raw_token: str, new_password: str) -> None:
        token = await self.password_reset_tokens.get_valid_by_hash(hash_opaque_token(raw_token))
        if token is None:
            raise ValidationAppError("This password reset link is invalid or has expired.")
        user = await self.users.get_by_id(token.user_id)
        if user is None:
            raise ValidationAppError("This password reset link is invalid or has expired.")

        await self.users.set_password(user, await hash_password_async(new_password))
        await self.password_reset_tokens.mark_used(token)
        # Invalidate all existing sessions on password change.
        await self.refresh_tokens.revoke_all_for_user(user.id)

    # ------------------------------------------------------------------
    async def change_password(
        self, *, user_id: uuid.UUID, current_password: str, new_password: str
    ) -> None:
        """Verifies `current_password` against the same Argon2 check used at
        login, then rotates the password and revokes every other session's
        refresh tokens -- matching the same "revoke on use" security posture
        `reset_password` already follows."""
        user = await self.users.get_by_id(user_id)
        if user is None or not await verify_password_async(current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect.")

        await self.users.set_password(user, await hash_password_async(new_password))
        await self.refresh_tokens.revoke_all_for_user(user.id)

    # ------------------------------------------------------------------
    async def get_current_user(self, *, access_token: str) -> User:
        from app.core.security import try_decode_token

        payload = try_decode_token(access_token)
        if payload is None or payload.get("type") != "access":
            raise UnauthorizedError("Invalid or expired access token.")

        try:
            user_id = uuid.UUID(payload["sub"])
        except (KeyError, ValueError) as exc:
            raise UnauthorizedError("Invalid or expired access token.") from exc

        user = await self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid or expired access token.")
        return user


async def deliver_email(message: EmailMessage) -> None:
    """Background-task entry point: sends an email after the HTTP response
    has gone out. Failures are logged (never raised) -- by this point the
    client already has its response, and a mail outage must not look like
    a failed signup."""
    from app.core.logging import logger
    from app.email.factory import get_email_sender

    try:
        result = await get_email_sender().send(message)
        if result is not None and not result.success:
            logger.error("Email delivery failed (subject=%r).", message.subject)
    except Exception:
        logger.exception("Email delivery raised (subject=%r).", message.subject)
