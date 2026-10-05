from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.core.exceptions import NotFoundError
from app.models.user import User
from app.schemas.health_profile import HealthProfileRead, HealthProfileUpsert
from app.services.health_profile_service import HealthProfileService

router = APIRouter(prefix="/profile", tags=["health-profile"])


@router.get("", response_model=HealthProfileRead)
async def get_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = HealthProfileService(session)
    profile = await service.get(user_id=current_user.id)
    if profile is None:
        raise NotFoundError("You haven't created a health profile yet.")
    return HealthProfileRead.model_validate(profile)


@router.put("", response_model=HealthProfileRead)
async def upsert_profile(
    payload: HealthProfileUpsert,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = HealthProfileService(session)
    profile = await service.upsert(user_id=current_user.id, data=payload)
    return HealthProfileRead.model_validate(profile)
