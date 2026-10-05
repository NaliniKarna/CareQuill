import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.medication import Medication


class MedicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, patient_id: uuid.UUID, **fields) -> Medication:
        medication = Medication(patient_id=patient_id, **fields)
        self.session.add(medication)
        await self.session.flush()
        return medication

    async def get_by_id_for_patient(
        self, medication_id: uuid.UUID, patient_id: uuid.UUID
    ) -> Medication | None:
        result = await self.session.execute(
            select(Medication).where(
                Medication.id == medication_id, Medication.patient_id == patient_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_patient(
        self,
        patient_id: uuid.UUID,
        *,
        active: bool | None = None,
        q: str | None = None,
    ) -> list[Medication]:
        filters = [Medication.patient_id == patient_id]
        if active is not None:
            filters.append(Medication.is_active.is_(active))
        if q:
            filters.append(Medication.name.ilike(f"%{q}%"))
        result = await self.session.execute(
            select(Medication).where(*filters).order_by(Medication.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_active_for_patient(self, patient_id: uuid.UUID) -> list[Medication]:
        return await self.list_for_patient(patient_id, active=True)

    async def update(self, medication: Medication, **fields) -> Medication:
        for key, value in fields.items():
            setattr(medication, key, value)
        await self.session.flush()
        return medication

    async def delete(self, medication: Medication) -> None:
        await self.session.delete(medication)
        await self.session.flush()
