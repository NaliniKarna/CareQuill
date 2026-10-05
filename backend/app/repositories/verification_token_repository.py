import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verification_token import EmailVerificationToken, PasswordResetToken


class EmailVerificationTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> EmailVerificationToken:
        token = EmailVerificationToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_valid_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        result = await self.session.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        )
        token = result.scalar_one_or_none()
        if token is None:
            return None
        if token.used_at is not None or token.expires_at < datetime.now(UTC):
            return None
        return token

    async def mark_used(self, token: EmailVerificationToken) -> None:
        token.used_at = datetime.now(UTC)
        await self.session.flush()


class PasswordResetTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, user_id: uuid.UUID, token_hash: str, expires_at: datetime
    ) -> PasswordResetToken:
        token = PasswordResetToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_valid_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self.session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        token = result.scalar_one_or_none()
        if token is None:
            return None
        if token.used_at is not None or token.expires_at < datetime.now(UTC):
            return None
        return token

    async def mark_used(self, token: PasswordResetToken) -> None:
        token.used_at = datetime.now(UTC)
        await self.session.flush()
