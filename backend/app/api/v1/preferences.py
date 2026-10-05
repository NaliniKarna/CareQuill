from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.preference import UserPreferenceRead, UserPreferenceUpdate
from app.services.preference_service import PreferenceService

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=UserPreferenceRead)
async def get_preferences(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Notification preferences and the data-sharing consent setting.
    Created with defaults on first read if they don't exist yet."""
    service = PreferenceService(session)
    preference = await service.get_or_create(user_id=current_user.id)
    return UserPreferenceRead.model_validate(preference)


@router.put("", response_model=UserPreferenceRead)
async def update_preferences(
    payload: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Partial update: only the fields provided are changed. Turning off
    `data_sharing_consent` stops future document uploads from being
    auto-processed by OCR/AI (see DocumentProcessingService)."""
    service = PreferenceService(session)
    preference = await service.update(user_id=current_user.id, data=payload)
    return UserPreferenceRead.model_validate(preference)
