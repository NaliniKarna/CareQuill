import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.doctor_contact import DoctorContact
from app.repositories.doctor_contact_repository import DoctorContactRepository
from app.schemas.doctor_contact import DoctorContactCreate, DoctorContactUpdate


class DoctorContactService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DoctorContactRepository(session)

    async def create(self, *, patient_id: uuid.UUID, data: DoctorContactCreate) -> DoctorContact:
        return await self.repo.create(patient_id=patient_id, **data.model_dump())

    async def list(self, *, patient_id: uuid.UUID) -> list[DoctorContact]:
        return await self.repo.list_for_patient(patient_id)

    async def get(self, *, patient_id: uuid.UUID, doctor_id: uuid.UUID) -> DoctorContact:
        doctor = await self.repo.get_by_id_for_patient(doctor_id, patient_id)
        if doctor is None:
            raise NotFoundError("Doctor contact not found.")
        return doctor

    async def update(
        self, *, patient_id: uuid.UUID, doctor_id: uuid.UUID, data: DoctorContactUpdate
    ) -> DoctorContact:
        doctor = await self.get(patient_id=patient_id, doctor_id=doctor_id)
        return await self.repo.update(doctor, **data.model_dump())

    async def delete(self, *, patient_id: uuid.UUID, doctor_id: uuid.UUID) -> None:
        doctor = await self.get(patient_id=patient_id, doctor_id=doctor_id)
        await self.repo.delete(doctor)
