import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.appointment import AppointmentCreate, AppointmentRead, AppointmentUpdate
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentRead, status_code=201)
async def create_appointment(
    payload: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    appointment = await service.create(patient_id=current_user.id, data=payload)
    return AppointmentRead.model_validate(appointment)


@router.get("", response_model=list[AppointmentRead])
async def list_appointments(
    filter: str | None = Query(default=None, pattern="^(upcoming|past)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    appointments = await service.list(patient_id=current_user.id, filter=filter)
    return [AppointmentRead.model_validate(a) for a in appointments]


@router.get("/{appointment_id}", response_model=AppointmentRead)
async def get_appointment(
    appointment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    appointment = await service.get(patient_id=current_user.id, appointment_id=appointment_id)
    return AppointmentRead.model_validate(appointment)


@router.put("/{appointment_id}", response_model=AppointmentRead)
async def update_appointment(
    appointment_id: uuid.UUID,
    payload: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    appointment = await service.update(
        patient_id=current_user.id, appointment_id=appointment_id, data=payload
    )
    return AppointmentRead.model_validate(appointment)


@router.delete("/{appointment_id}", status_code=204)
async def delete_appointment(
    appointment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    await service.delete(patient_id=current_user.id, appointment_id=appointment_id)


@router.patch("/{appointment_id}/cancel", response_model=AppointmentRead)
async def cancel_appointment(
    appointment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    appointment = await service.cancel(patient_id=current_user.id, appointment_id=appointment_id)
    return AppointmentRead.model_validate(appointment)


@router.patch("/{appointment_id}/complete", response_model=AppointmentRead)
async def complete_appointment(
    appointment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    appointment = await service.complete(
        patient_id=current_user.id, appointment_id=appointment_id
    )
    return AppointmentRead.model_validate(appointment)


@router.patch("/{appointment_id}/miss", response_model=AppointmentRead)
async def miss_appointment(
    appointment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = AppointmentService(session)
    appointment = await service.miss(patient_id=current_user.id, appointment_id=appointment_id)
    return AppointmentRead.model_validate(appointment)
