import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.models.appointment import Appointment
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.doctor_contact_repository import DoctorContactRepository
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate
from app.services.health_snapshot_service import HealthSnapshotService

_TERMINAL_STATUSES = {"completed", "cancelled", "missed"}


class AppointmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AppointmentRepository(session)
        self.doctors = DoctorContactRepository(session)
        self.snapshots = HealthSnapshotService(session)

    async def _ensure_doctor_owned(
        self, *, patient_id: uuid.UUID, doctor_contact_id: uuid.UUID | None
    ) -> None:
        if doctor_contact_id is None:
            return
        doctor = await self.doctors.get_by_id_for_patient(doctor_contact_id, patient_id)
        if doctor is None:
            # Another IDOR angle: don't let a patient attach someone else's
            # doctor-contact id to their own appointment.
            raise NotFoundError("Doctor contact not found.")

    async def create(self, *, patient_id: uuid.UUID, data: AppointmentCreate) -> Appointment:
        await self._ensure_doctor_owned(
            patient_id=patient_id, doctor_contact_id=data.doctor_contact_id
        )
        appointment = await self.repo.create(
            patient_id=patient_id, status="scheduled", **data.model_dump()
        )
        await self.snapshots.generate(patient_id=patient_id)
        return appointment

    async def list(
        self, *, patient_id: uuid.UUID, filter: str | None = None
    ) -> list[Appointment]:
        return await self.repo.list_for_patient(patient_id, filter=filter)

    async def get(self, *, patient_id: uuid.UUID, appointment_id: uuid.UUID) -> Appointment:
        appointment = await self.repo.get_by_id_for_patient(appointment_id, patient_id)
        if appointment is None:
            raise NotFoundError("Appointment not found.")
        return appointment

    async def update(
        self, *, patient_id: uuid.UUID, appointment_id: uuid.UUID, data: AppointmentUpdate
    ) -> Appointment:
        appointment = await self.get(patient_id=patient_id, appointment_id=appointment_id)
        fields = data.model_dump(exclude_unset=True)
        if "doctor_contact_id" in fields:
            await self._ensure_doctor_owned(
                patient_id=patient_id, doctor_contact_id=fields["doctor_contact_id"]
            )
        updated = await self.repo.update(appointment, **fields)
        await self.snapshots.generate(patient_id=patient_id)
        return updated

    async def delete(self, *, patient_id: uuid.UUID, appointment_id: uuid.UUID) -> None:
        appointment = await self.get(patient_id=patient_id, appointment_id=appointment_id)
        await self.repo.delete(appointment)
        await self.snapshots.generate(patient_id=patient_id)

    async def _transition(
        self, *, patient_id: uuid.UUID, appointment_id: uuid.UUID, new_status: str
    ) -> Appointment:
        appointment = await self.get(patient_id=patient_id, appointment_id=appointment_id)
        if appointment.status in _TERMINAL_STATUSES:
            raise ValidationAppError(
                f"Appointment is already {appointment.status} and cannot be "
                f"changed to {new_status}."
            )
        updated = await self.repo.update(appointment, status=new_status)
        await self.snapshots.generate(patient_id=patient_id)
        return updated

    async def cancel(self, *, patient_id: uuid.UUID, appointment_id: uuid.UUID) -> Appointment:
        return await self._transition(
            patient_id=patient_id, appointment_id=appointment_id, new_status="cancelled"
        )

    async def complete(self, *, patient_id: uuid.UUID, appointment_id: uuid.UUID) -> Appointment:
        return await self._transition(
            patient_id=patient_id, appointment_id=appointment_id, new_status="completed"
        )

    async def miss(self, *, patient_id: uuid.UUID, appointment_id: uuid.UUID) -> Appointment:
        return await self._transition(
            patient_id=patient_id, appointment_id=appointment_id, new_status="missed"
        )
