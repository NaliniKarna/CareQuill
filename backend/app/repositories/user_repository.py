import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def create(self, *, email: str, password_hash: str, **fields) -> User:
        user = User(email=email.lower(), password_hash=password_hash, **fields)
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_password(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        await self.session.flush()

    async def mark_verified(self, user: User) -> None:
        user.is_verified = True
        await self.session.flush()
