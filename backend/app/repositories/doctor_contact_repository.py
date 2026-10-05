import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doctor_contact import DoctorContact


class DoctorContactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, patient_id: uuid.UUID, **fields) -> DoctorContact:
        doctor = DoctorContact(patient_id=patient_id, **fields)
        self.session.add(doctor)
        await self.session.flush()
        return doctor

    async def get_by_id_for_patient(
        self, doctor_id: uuid.UUID, patient_id: uuid.UUID
    ) -> DoctorContact | None:
        result = await self.session.execute(
            select(DoctorContact).where(
                DoctorContact.id == doctor_id, DoctorContact.patient_id == patient_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_patient(self, patient_id: uuid.UUID) -> list[DoctorContact]:
        result = await self.session.execute(
            select(DoctorContact)
            .where(DoctorContact.patient_id == patient_id)
            .order_by(DoctorContact.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, doctor: DoctorContact, **fields) -> DoctorContact:
        for key, value in fields.items():
            setattr(doctor, key, value)
        await self.session.flush()
        return doctor

    async def delete(self, doctor: DoctorContact) -> None:
        await self.session.delete(doctor)
        await self.session.flush()
