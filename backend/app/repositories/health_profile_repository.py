import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_profile import HealthProfile


class HealthProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> HealthProfile | None:
        result = await self.session.execute(
            select(HealthProfile).where(HealthProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, *, user_id: uuid.UUID, **fields) -> HealthProfile:
        profile = HealthProfile(user_id=user_id, **fields)
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def update(self, profile: HealthProfile, **fields) -> HealthProfile:
        for key, value in fields.items():
            setattr(profile, key, value)
        await self.session.flush()
        return profile
