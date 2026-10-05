import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_profile import HealthProfile
from app.repositories.health_profile_repository import HealthProfileRepository
from app.schemas.health_profile import HealthProfileUpsert
from app.services.audit_service import AuditService


class HealthProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = HealthProfileRepository(session)
        self.audit = AuditService(session)

    async def get(self, *, user_id: uuid.UUID) -> HealthProfile | None:
        return await self.repo.get_by_user_id(user_id)

    async def upsert(self, *, user_id: uuid.UUID, data: HealthProfileUpsert) -> HealthProfile:
        existing = await self.repo.get_by_user_id(user_id)
        fields = data.model_dump()
        if existing is None:
            profile = await self.repo.create(user_id=user_id, **fields)
        else:
            profile = await self.repo.update(existing, **fields)
        await self.audit.record(
            user_id=user_id,
            event_type="health_profile_update",
            resource_type="health_profile",
            resource_id=profile.id,
        )
        return profile

    @staticmethod
    def completion_percent(profile: HealthProfile | None) -> int:
        if profile is None:
            return 0
        fields = [
            profile.first_name,
            profile.last_name,
            profile.date_of_birth,
            profile.gender,
            profile.blood_group,
            profile.phone,
            profile.address,
            profile.emergency_contact_name,
            profile.emergency_contact_phone,
            profile.height,
            profile.weight,
        ]
        filled = sum(1 for f in fields if f not in (None, ""))
        return round((filled / len(fields)) * 100)
