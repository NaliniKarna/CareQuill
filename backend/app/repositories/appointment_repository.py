import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment

_PAST_STATUSES = ("completed", "cancelled", "missed")


class AppointmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, *, patient_id: uuid.UUID, **fields) -> Appointment:
        appointment = Appointment(patient_id=patient_id, **fields)
        self.session.add(appointment)
        await self.session.flush()
        return appointment

    async def get_by_id_for_patient(
        self, appointment_id: uuid.UUID, patient_id: uuid.UUID
    ) -> Appointment | None:
        result = await self.session.execute(
            select(Appointment).where(
                Appointment.id == appointment_id, Appointment.patient_id == patient_id
            )
        )
        return result.scalar_one_or_none()

    async def list_for_patient(
        self, patient_id: uuid.UUID, *, filter: str | None = None
    ) -> list[Appointment]:
        query = select(Appointment).where(Appointment.patient_id == patient_id)
        today = date.today()
        if filter == "upcoming":
            query = query.where(
                Appointment.status == "scheduled", Appointment.appointment_date >= today
            )
            query = query.order_by(Appointment.appointment_date.asc())
        elif filter == "past":
            query = query.where(
                (Appointment.appointment_date < today) | (Appointment.status.in_(_PAST_STATUSES))
            )
            query = query.order_by(Appointment.appointment_date.desc())
        else:
            query = query.order_by(Appointment.appointment_date.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_relevant_for_snapshot(self, patient_id: uuid.UUID) -> list[Appointment]:
        """Upcoming scheduled + recently completed appointments, used to
        build a health snapshot."""
        result = await self.session.execute(
            select(Appointment)
            .where(Appointment.patient_id == patient_id, Appointment.status != "cancelled")
            .order_by(Appointment.appointment_date.desc())
            .limit(20)
        )
        return list(result.scalars().all())

    async def update(self, appointment: Appointment, **fields) -> Appointment:
        for key, value in fields.items():
            setattr(appointment, key, value)
        await self.session.flush()
        return appointment

    async def delete(self, appointment: Appointment) -> None:
        await self.session.delete(appointment)
        await self.session.flush()
