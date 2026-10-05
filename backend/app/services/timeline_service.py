"""
Aggregates a chronological health timeline on read -- no dedicated "events"
table for existing sources (conditions, medications, documents,
appointments); only freeform `TimelineNote`s are stored directly.

Tagging rule (per product spec): anything the patient entered directly into
a structured table (conditions, medications, documents, appointments) is
"VERIFIED" in this app's sense -- patient-asserted structured data, not
doctor-verified. Freeform notes are "PATIENT_PROVIDED". Anything sourced
from a reviewed `document_extractions.extracted_data` blob is
"AI_EXTRACTED", always -- never upgraded to VERIFIED automatically, even
after the patient reviews it (review only changes the extraction's own
status; it never writes into a verified table).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.document_extraction_repository import DocumentExtractionRepository
from app.repositories.medical_condition_repository import MedicalConditionRepository
from app.repositories.medical_document_repository import MedicalDocumentRepository
from app.repositories.medication_repository import MedicationRepository
from app.repositories.timeline_note_repository import TimelineNoteRepository
from app.schemas.timeline import TimelineEntry

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%B %d, %Y",
    "%B %d %Y",
)


def _parse_loose_date(value: str) -> date | None:
    cleaned = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


class TimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.conditions = MedicalConditionRepository(session)
        self.medications = MedicationRepository(session)
        self.documents = MedicalDocumentRepository(session)
        self.appointments = AppointmentRepository(session)
        self.notes = TimelineNoteRepository(session)
        self.extractions = DocumentExtractionRepository(session)

    async def get_timeline(
        self,
        *,
        patient_id: uuid.UUID,
        entry_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[TimelineEntry]:
        entries: list[TimelineEntry] = []
        entries.extend(await self._condition_entries(patient_id))
        entries.extend(await self._medication_entries(patient_id))
        entries.extend(await self._document_entries(patient_id))
        entries.extend(await self._appointment_entries(patient_id))
        entries.extend(await self._note_entries(patient_id))
        entries.extend(await self._ai_extracted_entries(patient_id))

        if entry_type:
            entries = [e for e in entries if e.type == entry_type]
        if date_from:
            entries = [e for e in entries if e.date >= date_from]
        if date_to:
            entries = [e for e in entries if e.date <= date_to]

        entries.sort(key=lambda e: e.date, reverse=True)
        return entries

    async def _condition_entries(self, patient_id: uuid.UUID) -> list[TimelineEntry]:
        conditions = await self.conditions.list_for_patient(patient_id)
        return [
            TimelineEntry(
                date=c.diagnosed_date,
                type="condition",
                title=c.name,
                detail=c.status,
                source_id=c.id,
                tag="VERIFIED",
            )
            for c in conditions
            if c.diagnosed_date is not None
        ]

    async def _medication_entries(self, patient_id: uuid.UUID) -> list[TimelineEntry]:
        medications = await self.medications.list_for_patient(patient_id)
        return [
            TimelineEntry(
                date=m.start_date,
                type="medication",
                title=m.name,
                detail=m.dosage,
                source_id=m.id,
                tag="VERIFIED",
            )
            for m in medications
            if m.start_date is not None
        ]

    async def _document_entries(self, patient_id: uuid.UUID) -> list[TimelineEntry]:
        documents = await self.documents.list_all_for_patient(patient_id)
        return [
            TimelineEntry(
                date=d.visit_date or d.created_at.date(),
                type="document",
                title=d.title,
                detail=d.category,
                source_id=d.id,
                tag="VERIFIED",
            )
            for d in documents
        ]

    async def _appointment_entries(self, patient_id: uuid.UUID) -> list[TimelineEntry]:
        appointments = await self.appointments.list_for_patient(patient_id)
        return [
            TimelineEntry(
                date=a.appointment_date,
                type="appointment",
                title=a.reason or "Appointment",
                detail=a.status,
                source_id=a.id,
                tag="VERIFIED",
            )
            for a in appointments
        ]

    async def _note_entries(self, patient_id: uuid.UUID) -> list[TimelineEntry]:
        notes = await self.notes.list_for_patient(patient_id)
        return [
            TimelineEntry(
                date=n.event_date,
                type="note",
                title=(n.note_text[:80] + "…") if len(n.note_text) > 80 else n.note_text,
                detail=n.note_text,
                source_id=n.id,
                tag="PATIENT_PROVIDED",
            )
            for n in notes
        ]

    async def _ai_extracted_entries(self, patient_id: uuid.UUID) -> list[TimelineEntry]:
        reviewed = await self.extractions.list_reviewed_for_patient(patient_id)
        entries: list[TimelineEntry] = []
        for extraction in reviewed:
            data = extraction.extracted_data or {}
            summary_bits = []
            if data.get("medications"):
                summary_bits.append(f"{len(data['medications'])} medication(s)")
            if data.get("conditions"):
                summary_bits.append(f"{len(data['conditions'])} condition(s)")
            if data.get("lab_values"):
                summary_bits.append(f"{len(data['lab_values'])} lab value(s)")
            detail = ", ".join(summary_bits) or None

            for raw_date in data.get("dates") or []:
                parsed = _parse_loose_date(raw_date)
                if parsed is None:
                    continue
                entries.append(
                    TimelineEntry(
                        date=parsed,
                        type="ai_extracted",
                        title="AI-extracted information",
                        detail=detail,
                        source_id=extraction.id,
                        tag="AI_EXTRACTED",
                    )
                )
        return entries
