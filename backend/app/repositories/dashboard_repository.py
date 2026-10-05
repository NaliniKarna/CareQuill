"""
Read-only aggregate queries for the dashboard. Kept as its own repository
(rather than reusing per-domain repositories) because these are
cross-entity, dashboard-specific reads, not CRUD on a single table -- the
domain repositories for medications/appointments/documents/etc. will land
with the checkpoints that add full CRUD for those features.
"""
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_summary import AISummary
from app.models.appointment import Appointment
from app.models.doctor_contact import DoctorContact
from app.models.health_snapshot import HealthSnapshot
from app.models.medical_document import MedicalDocument
from app.models.medication import Medication
from app.models.medication_reminder import MedicationReminder


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_active_medications(self, patient_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Medication)
            .where(Medication.patient_id == patient_id, Medication.is_active.is_(True))
        )
        return result.scalar_one()

    async def count_recent_documents(self, patient_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(MedicalDocument)
            .where(MedicalDocument.patient_id == patient_id)
        )
        return result.scalar_one()

    async def get_next_appointment(
        self, patient_id: uuid.UUID
    ) -> tuple[Appointment, str | None] | None:
        """Returns the appointment plus its doctor contact's name (via an
        outer join, since doctor_contact_id is optional), rather than just
        the bare appointment row -- the dashboard needs a display name, not
        another round trip."""
        result = await self.session.execute(
            select(Appointment, DoctorContact.name)
            .outerjoin(DoctorContact, DoctorContact.id == Appointment.doctor_contact_id)
            .where(
                Appointment.patient_id == patient_id,
                Appointment.appointment_date >= date.today(),
                Appointment.status == "scheduled",
            )
            .order_by(Appointment.appointment_date.asc())
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None
        appointment, doctor_name = row
        return appointment, doctor_name

    async def count_reminders_due_today(self, patient_id: uuid.UUID) -> int:
        """Reminders are stored as "daily" or a comma-separated subset of
        3-letter day codes (see MedicationReminderBase). Matching that
        against "today" is easiest done in Python once enabled reminders
        for active medications are fetched -- the set per patient is small,
        and it avoids a fragile SQL substring match."""
        result = await self.session.execute(
            select(MedicationReminder.days_of_week)
            .join(Medication, Medication.id == MedicationReminder.medication_id)
            .where(
                MedicationReminder.patient_id == patient_id,
                MedicationReminder.is_enabled.is_(True),
                Medication.is_active.is_(True),
            )
        )
        today_code = date.today().strftime("%a").lower()
        count = 0
        for (days_of_week,) in result.all():
            if days_of_week == "daily" or today_code in days_of_week.split(","):
                count += 1
        return count

    async def has_health_snapshot(self, patient_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(func.count())
            .select_from(HealthSnapshot)
            .where(HealthSnapshot.patient_id == patient_id)
        )
        return result.scalar_one() > 0

    async def get_latest_ai_summary(self, patient_id: uuid.UUID) -> AISummary | None:
        result = await self.session.execute(
            select(AISummary)
            .where(AISummary.patient_id == patient_id)
            .order_by(AISummary.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
