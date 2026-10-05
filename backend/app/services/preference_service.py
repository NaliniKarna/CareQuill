import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preference import DEFAULT_NOTIFICATION_PREFS, UserPreference
from app.repositories.user_preference_repository import UserPreferenceRepository
from app.schemas.preference import UserPreferenceUpdate


class PreferenceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserPreferenceRepository(session)

    async def get_or_create(self, *, user_id: uuid.UUID) -> UserPreference:
        """Preferences are lazily created with defaults on first read/write
        -- there is no separate "create" step in the product flow; every
        user implicitly has default preferences from registration."""
        existing = await self.repo.get_by_user_id(user_id)
        if existing is not None:
            return existing
        return await self.repo.create(
            user_id=user_id,
            notification_prefs=dict(DEFAULT_NOTIFICATION_PREFS),
            data_sharing_consent=True,
        )

    async def update(
        self, *, user_id: uuid.UUID, data: UserPreferenceUpdate
    ) -> UserPreference:
        preference = await self.get_or_create(user_id=user_id)
        fields = data.model_dump(exclude_unset=True, exclude_none=True)
        if "notification_prefs" in fields:
            fields["notification_prefs"] = dict(fields["notification_prefs"])
        return await self.repo.update(preference, **fields)

    async def get_data_sharing_consent(self, *, user_id: uuid.UUID) -> bool:
        """Cheap read used by DocumentProcessingService to decide whether
        OCR/AI processing may run for this patient's uploads."""
        preference = await self.repo.get_by_user_id(user_id)
        if preference is None:
            return True  # default: consent on, matches the model column default
        return preference.data_sharing_consent
