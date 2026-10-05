import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.allergy import AllergyCreate, AllergyRead, AllergyUpdate
from app.services.allergy_service import AllergyService

router = APIRouter(prefix="/allergies", tags=["allergies"])


@router.post("", response_model=AllergyRead, status_code=201)
async def create_allergy(
    payload: AllergyCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AllergyService(session)
    allergy = await service.create(patient_id=current_user.id, data=payload)
    return AllergyRead.model_validate(allergy)


@router.get("", response_model=list[AllergyRead])
async def list_allergies(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AllergyService(session)
    allergies = await service.list(patient_id=current_user.id)
    return [AllergyRead.model_validate(a) for a in allergies]


@router.get("/{allergy_id}", response_model=AllergyRead)
async def get_allergy(
    allergy_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AllergyService(session)
    allergy = await service.get(patient_id=current_user.id, allergy_id=allergy_id)
    return AllergyRead.model_validate(allergy)


@router.put("/{allergy_id}", response_model=AllergyRead)
async def update_allergy(
    allergy_id: uuid.UUID,
    payload: AllergyUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AllergyService(session)
    allergy = await service.update(
        patient_id=current_user.id, allergy_id=allergy_id, data=payload
    )
    return AllergyRead.model_validate(allergy)


@router.delete("/{allergy_id}", status_code=204)
async def delete_allergy(
    allergy_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AllergyService(session)
    await service.delete(patient_id=current_user.id, allergy_id=allergy_id)
