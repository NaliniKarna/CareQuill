import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.doctor_contact import DoctorContactCreate, DoctorContactRead, DoctorContactUpdate
from app.services.doctor_contact_service import DoctorContactService

router = APIRouter(prefix="/doctors", tags=["doctor-contacts"])


@router.post("", response_model=DoctorContactRead, status_code=201)
async def create_doctor(
    payload: DoctorContactCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DoctorContactService(session)
    doctor = await service.create(patient_id=current_user.id, data=payload)
    return DoctorContactRead.model_validate(doctor)


@router.get("", response_model=list[DoctorContactRead])
async def list_doctors(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DoctorContactService(session)
    doctors = await service.list(patient_id=current_user.id)
    return [DoctorContactRead.model_validate(d) for d in doctors]


@router.get("/{doctor_id}", response_model=DoctorContactRead)
async def get_doctor(
    doctor_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DoctorContactService(session)
    doctor = await service.get(patient_id=current_user.id, doctor_id=doctor_id)
    return DoctorContactRead.model_validate(doctor)


@router.put("/{doctor_id}", response_model=DoctorContactRead)
async def update_doctor(
    doctor_id: uuid.UUID,
    payload: DoctorContactUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DoctorContactService(session)
    doctor = await service.update(patient_id=current_user.id, doctor_id=doctor_id, data=payload)
    return DoctorContactRead.model_validate(doctor)


@router.delete("/{doctor_id}", status_code=204)
async def delete_doctor(
    doctor_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = DoctorContactService(session)
    await service.delete(patient_id=current_user.id, doctor_id=doctor_id)
