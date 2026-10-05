import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.medication_reminder import MedicationReminder
from app.repositories.medication_reminder_repository import MedicationReminderRepository
from app.repositories.medication_repository import MedicationRepository
from app.schemas.medication_reminder import MedicationReminderCreate, MedicationReminderUpdate


class MedicationReminderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MedicationReminderRepository(session)
        self.medications = MedicationRepository(session)

    async def _ensure_medication_owned(
        self, *, patient_id: uuid.UUID, medication_id: uuid.UUID
    ) -> None:
        medication = await self.medications.get_by_id_for_patient(medication_id, patient_id)
        if medication is None:
            raise NotFoundError("Medication not found.")

    async def create(
        self,
        *,
        patient_id: uuid.UUID,
        medication_id: uuid.UUID,
        data: MedicationReminderCreate,
    ) -> MedicationReminder:
        await self._ensure_medication_owned(patient_id=patient_id, medication_id=medication_id)
        return await self.repo.create(
            medication_id=medication_id, patient_id=patient_id, **data.model_dump()
        )

    async def list(
        self, *, patient_id: uuid.UUID, medication_id: uuid.UUID
    ) -> list[MedicationReminder]:
        await self._ensure_medication_owned(patient_id=patient_id, medication_id=medication_id)
        return await self.repo.list_for_medication(medication_id, patient_id)

    async def get(
        self, *, patient_id: uuid.UUID, medication_id: uuid.UUID, reminder_id: uuid.UUID
    ) -> MedicationReminder:
        reminder = await self.repo.get_by_id_for_patient(reminder_id, patient_id)
        if reminder is None or reminder.medication_id != medication_id:
            raise NotFoundError("Reminder not found.")
        return reminder

    async def update(
        self,
        *,
        patient_id: uuid.UUID,
        medication_id: uuid.UUID,
        reminder_id: uuid.UUID,
        data: MedicationReminderUpdate,
    ) -> MedicationReminder:
        reminder = await self.get(
            patient_id=patient_id, medication_id=medication_id, reminder_id=reminder_id
        )
        fields = data.model_dump(exclude_unset=True)
        return await self.repo.update(reminder, **fields)

    async def delete(
        self, *, patient_id: uuid.UUID, medication_id: uuid.UUID, reminder_id: uuid.UUID
    ) -> None:
        reminder = await self.get(
            patient_id=patient_id, medication_id=medication_id, reminder_id=reminder_id
        )
        await self.repo.delete(reminder)
