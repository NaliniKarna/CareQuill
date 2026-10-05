import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication_reminder import MedicationReminder


class MedicationReminderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, medication_id: uuid.UUID, patient_id: uuid.UUID, **fields
    ) -> MedicationReminder:
        reminder = MedicationReminder(medication_id=medication_id, patient_id=patient_id, **fields)
        self.session.add(reminder)
        await self.session.flush()
        return reminder

    async def get_by_id_for_patient(
        self, reminder_id: uuid.UUID, patient_id: uuid.UUID
    ) -> MedicationReminder | None:
        result = await self.session.execute(
            select(MedicationReminder).where(
                MedicationReminder.id == reminder_id,
                MedicationReminder.patient_id == patient_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_medication(
        self, medication_id: uuid.UUID, patient_id: uuid.UUID
    ) -> list[MedicationReminder]:
        result = await self.session.execute(
            select(MedicationReminder)
            .where(
                MedicationReminder.medication_id == medication_id,
                MedicationReminder.patient_id == patient_id,
            )
            .order_by(MedicationReminder.reminder_time.asc())
        )
        return list(result.scalars().all())

    async def list_for_patient(self, patient_id: uuid.UUID) -> list[MedicationReminder]:
        result = await self.session.execute(
            select(MedicationReminder)
            .where(MedicationReminder.patient_id == patient_id)
            .order_by(MedicationReminder.reminder_time.asc())
        )
        return list(result.scalars().all())

    async def update(self, reminder: MedicationReminder, **fields) -> MedicationReminder:
        for key, value in fields.items():
            setattr(reminder, key, value)
        await self.session.flush()
        return reminder

    async def delete(self, reminder: MedicationReminder) -> None:
        await self.session.delete(reminder)
        await self.session.flush()
