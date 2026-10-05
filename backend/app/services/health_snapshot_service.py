"""
Aggregates a patient's current *verified* structured data (medications,
allergies, conditions, doctor contacts, appointments -- everything the
patient entered directly, never AI-extracted suggestions) into an immutable,
versioned `HealthSnapshot`. This is a cheap JSON aggregation query only --
no AI call happens here; AI summary generation (a later task) consumes a
snapshot as its input.

`generate()` is called both from the dedicated
POST /api/v1/health-snapshots/generate endpoint AND automatically,
service-to-service, whenever a medication/allergy/condition/appointment is
created or changed -- see the `_regenerate` calls in those services -- so
the snapshot never silently goes stale.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.allergy import Allergy
from app.models.appointment import Appointment
from app.models.doctor_contact import DoctorContact
from app.models.health_snapshot import HealthSnapshot
from app.models.medical_condition import MedicalCondition
from app.models.medication import Medication
from app.repositories.ai_summary_repository import AISummaryRepository
from app.repositories.allergy_repository import AllergyRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.doctor_contact_repository import DoctorContactRepository
from app.repositories.health_snapshot_repository import HealthSnapshotRepository
from app.repositories.medical_condition_repository import MedicalConditionRepository
from app.repositories.medication_repository import MedicationRepository


class HealthSnapshotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.snapshots = HealthSnapshotRepository(session)
        self.ai_summaries = AISummaryRepository(session)
        self.medications = MedicationRepository(session)
        self.allergies = AllergyRepository(session)
        self.conditions = MedicalConditionRepository(session)
        self.doctors = DoctorContactRepository(session)
        self.appointments = AppointmentRepository(session)

    async def generate(self, *, patient_id: uuid.UUID) -> HealthSnapshot:
        snapshot_data = await self._build_snapshot_data(patient_id)

        latest = await self.snapshots.get_latest(patient_id)
        next_version = (latest.version + 1) if latest else 1

        snapshot = await self.snapshots.create(
            patient_id=patient_id, version=next_version, snapshot_data=snapshot_data
        )
        await self.ai_summaries.mark_stale_summaries_outdated(patient_id)
        return snapshot

    async def list_versions(self, *, patient_id: uuid.UUID) -> list[HealthSnapshot]:
        return await self.snapshots.list_versions_for_patient(patient_id)

    async def get_latest(self, *, patient_id: uuid.UUID) -> HealthSnapshot | None:
        return await self.snapshots.get_latest(patient_id)

    async def get_by_id(
        self, *, patient_id: uuid.UUID, snapshot_id: uuid.UUID
    ) -> HealthSnapshot | None:
        return await self.snapshots.get_by_id_for_patient(snapshot_id, patient_id)

    async def _build_snapshot_data(self, patient_id: uuid.UUID) -> dict:
        active_medications = await self.medications.list_active_for_patient(patient_id)
        allergies = await self.allergies.list_for_patient(patient_id)
        conditions = await self.conditions.list_for_patient(patient_id)
        doctors = await self.doctors.list_for_patient(patient_id)
        appointments = await self.appointments.list_relevant_for_snapshot(patient_id)

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "medications": [_serialize_medication(m) for m in active_medications],
            "allergies": [_serialize_allergy(a) for a in allergies],
            "conditions": [_serialize_condition(c) for c in conditions],
            "doctor_contacts": [_serialize_doctor(d) for d in doctors],
            "appointments": [_serialize_appointment(a) for a in appointments],
        }


def _serialize_medication(medication: Medication) -> dict:
    return {
        "id": str(medication.id),
        "name": medication.name,
        "dosage": medication.dosage,
        "frequency": medication.frequency,
        "instructions": medication.instructions,
        "start_date": medication.start_date.isoformat() if medication.start_date else None,
        "end_date": medication.end_date.isoformat() if medication.end_date else None,
        "notes": medication.notes,
    }


def _serialize_allergy(allergy: Allergy) -> dict:
    return {
        "id": str(allergy.id),
        "name": allergy.name,
        "severity": allergy.severity,
        "reaction": allergy.reaction,
        "notes": allergy.notes,
    }


def _serialize_condition(condition: MedicalCondition) -> dict:
    return {
        "id": str(condition.id),
        "name": condition.name,
        "diagnosed_date": (
            condition.diagnosed_date.isoformat() if condition.diagnosed_date else None
        ),
        "status": condition.status,
        "notes": condition.notes,
    }


def _serialize_doctor(doctor: DoctorContact) -> dict:
    return {
        "id": str(doctor.id),
        "name": doctor.name,
        "email": doctor.email,
        "phone": doctor.phone,
        "specialization": doctor.specialization,
        "clinic_name": doctor.clinic_name,
    }


def _serialize_appointment(appointment: Appointment) -> dict:
    return {
        "id": str(appointment.id),
        "appointment_date": appointment.appointment_date.isoformat(),
        "appointment_time": (
            appointment.appointment_time.isoformat() if appointment.appointment_time else None
        ),
        "reason": appointment.reason,
        "status": appointment.status,
        "doctor_contact_id": (
            str(appointment.doctor_contact_id) if appointment.doctor_contact_id else None
        ),
    }
