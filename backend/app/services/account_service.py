"""
Patient data control: export everything the patient has stored, and
permanently delete the account.

Export
------
A ZIP containing `data.json` (every record the patient owns, in readable
form) plus the ORIGINAL uploaded documents under `documents/`. Internal
details that are not the patient's data - password hash, token hashes,
storage paths - are never included.

Delete
------
Removes the user row; every patient-owned table has `ON DELETE CASCADE` on
`users.id`, so the database removes the rest in the same transaction. Stored
files are deleted only AFTER that transaction has committed (so a failed
commit can never leave records pointing at deleted files). Audit-log rows are
kept but anonymised by the existing `ON DELETE SET NULL`; they contain event
types and ids only, never medical content.
"""
from __future__ import annotations

import asyncio
import io
import json
import uuid
import zipfile
from datetime import UTC, datetime
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError, ValidationAppError
from app.core.logging import logger
from app.core.security import verify_password_async
from app.models.ai_summary import AISummary
from app.models.allergy import Allergy
from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from app.models.doctor_contact import DoctorContact
from app.models.document_extraction import DocumentExtraction
from app.models.email_log import EmailLog
from app.models.health_profile import HealthProfile
from app.models.health_snapshot import HealthSnapshot
from app.models.journal_entry import JournalEntry
from app.models.medical_condition import MedicalCondition
from app.models.medical_document import MedicalDocument
from app.models.medication import Medication
from app.models.medication_reminder import MedicationReminder
from app.models.notification import Notification
from app.models.timeline_note import TimelineNote
from app.models.user import User
from app.models.user_preference import UserPreference
from app.services.audit_service import AuditService
from app.storage.factory import get_storage_backend

DELETE_CONFIRMATION = "DELETE"

# Columns that are internal plumbing, not the patient's data.
_EXCLUDED_COLUMNS = frozenset({"password_hash", "storage_path", "stored_filename"})

# (key in data.json, model, ownership column)
_OWNED_TABLES: list[tuple[str, type, str]] = [
    ("health_profile", HealthProfile, "user_id"),
    ("preferences", UserPreference, "user_id"),
    ("medications", Medication, "patient_id"),
    ("medication_reminders", MedicationReminder, "patient_id"),
    ("allergies", Allergy, "patient_id"),
    ("conditions", MedicalCondition, "patient_id"),
    ("doctor_contacts", DoctorContact, "patient_id"),
    ("appointments", Appointment, "patient_id"),
    ("timeline_notes", TimelineNote, "patient_id"),
    ("journal_entries", JournalEntry, "patient_id"),
    ("health_snapshots", HealthSnapshot, "patient_id"),
    ("ai_summaries", AISummary, "patient_id"),
    ("emails_sent", EmailLog, "patient_id"),
    ("notifications", Notification, "patient_id"),
    ("activity_log", AuditLog, "user_id"),
]


def _row_to_dict(obj: Any) -> dict[str, Any]:
    mapper = inspect(obj).mapper
    return {
        attr.key: getattr(obj, attr.key)
        for attr in mapper.column_attrs
        if attr.key not in _EXCLUDED_COLUMNS
    }


def _safe_member_name(document: MedicalDocument) -> str:
    # `original_filename` is already sanitised at upload; the id prefix keeps
    # two files with the same name apart.
    return f"documents/{document.id}_{document.original_filename}"


def _build_zip(data: dict[str, Any], files: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        payload = json.dumps(jsonable_encoder(data), indent=2, ensure_ascii=False)
        archive.writestr("data.json", payload)
        for name, content in files:
            archive.writestr(name, content)
    return buffer.getvalue()


class AccountService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.storage = get_storage_backend()
        self.audit = AuditService(session)

    # ------------------------------------------------------------------
    async def export_zip(self, *, user: User) -> bytes:
        data: dict[str, Any] = {
            "exported_at": datetime.now(UTC),
            "account": {
                "id": user.id,
                "email": user.email,
                "created_at": user.created_at,
            },
        }
        for key, model, owner_column in _OWNED_TABLES:
            rows: Any = await self.session.execute(
                select(model).where(getattr(model, owner_column) == user.id)
            )
            data[key] = [_row_to_dict(row) for row in rows.scalars().all()]

        documents = (
            (
                await self.session.execute(
                    select(MedicalDocument).where(MedicalDocument.patient_id == user.id)
                )
            )
            .scalars()
            .all()
        )
        extractions = (
            (
                await self.session.execute(
                    select(DocumentExtraction).where(
                        DocumentExtraction.document_id.in_([d.id for d in documents])
                    )
                )
            )
            .scalars()
            .all()
            if documents
            else []
        )
        by_document: dict[uuid.UUID, list[dict[str, Any]]] = {}
        for extraction in extractions:
            by_document.setdefault(extraction.document_id, []).append(_row_to_dict(extraction))

        files: list[tuple[str, bytes]] = []
        document_entries: list[dict[str, Any]] = []
        for document in documents:
            entry = _row_to_dict(document)
            entry["extractions"] = by_document.get(document.id, [])
            try:
                content = await self.storage.read(storage_path=document.storage_path)
            except FileNotFoundError:
                entry["file_included"] = False
            else:
                member = _safe_member_name(document)
                files.append((member, content))
                entry["file_included"] = True
                entry["file_in_archive"] = member
            document_entries.append(entry)
        data["documents"] = document_entries

        await self.audit.record(user_id=user.id, event_type="data_export")
        return await asyncio.to_thread(_build_zip, data, files)

    # ------------------------------------------------------------------
    async def delete_account(self, *, user: User, password: str, confirmation: str) -> None:
        if confirmation != DELETE_CONFIRMATION:
            raise ValidationAppError(f'Type "{DELETE_CONFIRMATION}" to confirm account deletion.')
        if not await verify_password_async(password, user.password_hash):
            raise UnauthorizedError("Password is incorrect.")

        storage_paths = list(
            (
                await self.session.execute(
                    select(MedicalDocument.storage_path).where(
                        MedicalDocument.patient_id == user.id
                    )
                )
            )
            .scalars()
            .all()
        )
        user_id = user.id
        await self.session.execute(delete(User).where(User.id == user_id))
        # Commit BEFORE touching files: if this fails nothing was removed.
        await self.session.commit()
        logger.info("Account %s deleted (%d stored files to remove).", user_id, len(storage_paths))

        for path in storage_paths:
            try:
                await self.storage.delete(storage_path=path)
            except Exception:  # noqa: BLE001 - records are already gone; log and move on
                logger.exception("Could not remove stored file for deleted account %s.", user_id)
