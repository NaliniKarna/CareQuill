import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.medication import MedicationCreate, MedicationRead, MedicationUpdate
from app.schemas.medication_reminder import (
    MedicationReminderCreate,
    MedicationReminderRead,
    MedicationReminderUpdate,
)
from app.services.medication_reminder_service import MedicationReminderService
from app.services.medication_service import MedicationService

router = APIRouter(prefix="/medications", tags=["medications"])


@router.post("", response_model=MedicationRead, status_code=201)
async def create_medication(
    payload: MedicationCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicationService(session)
    medication = await service.create(patient_id=current_user.id, data=payload)
    return MedicationRead.model_validate(medication)


@router.get("", response_model=list[MedicationRead])
async def list_medications(
    active: bool | None = Query(default=None),
    q: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicationService(session)
    medications = await service.list(patient_id=current_user.id, active=active, q=q)
    return [MedicationRead.model_validate(m) for m in medications]


@router.get("/{medication_id}", response_model=MedicationRead)
async def get_medication(
    medication_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicationService(session)
    medication = await service.get(patient_id=current_user.id, medication_id=medication_id)
    return MedicationRead.model_validate(medication)


@router.put("/{medication_id}", response_model=MedicationRead)
async def update_medication(
    medication_id: uuid.UUID,
    payload: MedicationUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicationService(session)
    medication = await service.update(
        patient_id=current_user.id, medication_id=medication_id, data=payload
    )
    return MedicationRead.model_validate(medication)


@router.delete("/{medication_id}", status_code=204)
async def delete_medication(
    medication_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicationService(session)
    await service.delete(patient_id=current_user.id, medication_id=medication_id)


@router.patch("/{medication_id}/activate", response_model=MedicationRead)
async def activate_medication(
    medication_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicationService(session)
    medication = await service.set_active(
        patient_id=current_user.id, medication_id=medication_id, is_active=True
    )
    return MedicationRead.model_validate(medication)


@router.patch("/{medication_id}/deactivate", response_model=MedicationRead)
async def deactivate_medication(
    medication_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicationService(session)
    medication = await service.set_active(
        patient_id=current_user.id, medication_id=medication_id, is_active=False
    )
    return MedicationRead.model_validate(medication)


# --- Reminders (nested under a medication) -------------------------------


@router.post(
    "/{medication_id}/reminders", response_model=MedicationReminderRead, status_code=201
)
async def create_medication_reminder(
    medication_id: uuid.UUID,
    payload: MedicationReminderCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicationReminderService(session)
    reminder = await service.create(
        patient_id=current_user.id, medication_id=medication_id, data=payload
    )
    return MedicationReminderRead.model_validate(reminder)


@router.get("/{medication_id}/reminders", response_model=list[MedicationReminderRead])
async def list_medication_reminders(
    medication_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicationReminderService(session)
    reminders = await service.list(patient_id=current_user.id, medication_id=medication_id)
    return [MedicationReminderRead.model_validate(r) for r in reminders]


@router.patch(
    "/{medication_id}/reminders/{reminder_id}", response_model=MedicationReminderRead
)
async def update_medication_reminder(
    medication_id: uuid.UUID,
    reminder_id: uuid.UUID,
    payload: MedicationReminderUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicationReminderService(session)
    reminder = await service.update(
        patient_id=current_user.id,
        medication_id=medication_id,
        reminder_id=reminder_id,
        data=payload,
    )
    return MedicationReminderRead.model_validate(reminder)


@router.delete("/{medication_id}/reminders/{reminder_id}", status_code=204)
async def delete_medication_reminder(
    medication_id: uuid.UUID,
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    service = MedicationReminderService(session)
    await service.delete(
        patient_id=current_user.id, medication_id=medication_id, reminder_id=reminder_id
    )
