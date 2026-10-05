import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.medical_condition import (
    MedicalConditionCreate,
    MedicalConditionRead,
    MedicalConditionUpdate,
)
from app.services.medical_condition_service import MedicalConditionService

router = APIRouter(prefix="/conditions", tags=["conditions"])


@router.post("", response_model=MedicalConditionRead, status_code=201)
async def create_condition(
    payload: MedicalConditionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicalConditionService(session)
    condition = await service.create(patient_id=current_user.id, data=payload)
    return MedicalConditionRead.model_validate(condition)


@router.get("", response_model=list[MedicalConditionRead])
async def list_conditions(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicalConditionService(session)
    conditions = await service.list(patient_id=current_user.id)
    return [MedicalConditionRead.model_validate(c) for c in conditions]


@router.get("/{condition_id}", response_model=MedicalConditionRead)
async def get_condition(
    condition_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicalConditionService(session)
    condition = await service.get(patient_id=current_user.id, condition_id=condition_id)
    return MedicalConditionRead.model_validate(condition)


@router.put("/{condition_id}", response_model=MedicalConditionRead)
async def update_condition(
    condition_id: uuid.UUID,
    payload: MedicalConditionUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicalConditionService(session)
    condition = await service.update(
        patient_id=current_user.id, condition_id=condition_id, data=payload
    )
    return MedicalConditionRead.model_validate(condition)


@router.delete("/{condition_id}", status_code=204)
async def delete_condition(
    condition_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicalConditionService(session)
    await service.delete(patient_id=current_user.id, condition_id=condition_id)
