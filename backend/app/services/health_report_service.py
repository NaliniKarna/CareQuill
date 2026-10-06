"""
On-demand, patient-configured health report: preview what would be sent,
generate the PDF for the patient to download/review, and share it with a
doctor contact by email.

`preview()`, `generate_pdf()` and `share()` all take the identical request
shape (`HealthReportRequest`) on purpose. The product flow is "configure
once (pick a doctor, an appointment, which sections, which documents, which
reviewed AI summary), preview it, then either download the PDF or send the
same thing" -- so the three endpoints are really three different things to
*do* with one configuration, not three different configurations.

Every id the patient references (doctor, appointment, AI summary, each
document) is re-validated as belonging to `patient_id` on every call --
IDOR is checked fresh each time, never cached/trusted from a prior call.

`share()` IS the patient's confirmation: nothing is generated or sent by
`preview()` or `generate_pdf()`. The frontend gates the "send" action
behind a confirm click; this endpoint doesn't need a separate two-phase API.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationAppError
from app.email.factory import get_email_sender
from app.email.interface import EmailMessage
from app.email.templates import render_health_report_email
from app.models.ai_summary import AISummary
from app.models.allergy import Allergy
from app.models.appointment import Appointment
from app.models.doctor_contact import DoctorContact
from app.models.email_log import EmailLog
from app.models.medical_condition import MedicalCondition
from app.models.medical_document import MedicalDocument
from app.models.medication import Medication
from app.pdf.factory import get_pdf_generator
from app.repositories.ai_summary_repository import AISummaryRepository
from app.repositories.allergy_repository import AllergyRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.doctor_contact_repository import DoctorContactRepository
from app.repositories.email_log_repository import EmailLogRepository
from app.repositories.health_profile_repository import HealthProfileRepository
from app.repositories.medical_condition_repository import MedicalConditionRepository
from app.repositories.medical_document_repository import MedicalDocumentRepository
from app.repositories.medication_repository import MedicationRepository
from app.schemas.health_report import HealthReportPreview, HealthReportRequest
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.services.timeline_service import TimelineService
from app.storage.factory import get_storage_backend

_SHAREABLE_AI_SUMMARY_STATUSES = ("reviewed", "shared")
_TIMELINE_EXCERPT_LIMIT = 20


@dataclass
class _ReportContext:
    doctor: DoctorContact | None = None
    appointment: Appointment | None = None
    ai_summary: AISummary | None = None
    documents: list[MedicalDocument] = field(default_factory=list)
    conditions: list[MedicalCondition] = field(default_factory=list)
    allergies: list[Allergy] = field(default_factory=list)
    medications: list[Medication] = field(default_factory=list)
    timeline_entries: list = field(default_factory=list)
    patient_name: str = "Patient"
    patient_info: dict = field(default_factory=dict)


class HealthReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.doctors = DoctorContactRepository(session)
        self.appointments = AppointmentRepository(session)
        self.ai_summaries = AISummaryRepository(session)
        self.documents = MedicalDocumentRepository(session)
        self.conditions = MedicalConditionRepository(session)
        self.allergies = AllergyRepository(session)
        self.medications = MedicationRepository(session)
        self.health_profiles = HealthProfileRepository(session)
        self.email_logs = EmailLogRepository(session)
        self.timeline = TimelineService(session)
        self.storage = get_storage_backend()
        self.audit = AuditService(session)
        self.notifications = NotificationService(session)

    # -- preview --------------------------------------------------------------
    async def preview(
        self, *, patient_id: uuid.UUID, request: HealthReportRequest
    ) -> HealthReportPreview:
        ctx = await self._resolve_context(patient_id=patient_id, request=request)
        return HealthReportPreview(
            doctor_name=ctx.doctor.name if ctx.doctor else None,
            doctor_email=ctx.doctor.email if ctx.doctor else None,
            appointment_date=ctx.appointment.appointment_date if ctx.appointment else None,
            appointment_reason=ctx.appointment.reason if ctx.appointment else None,
            included_sections=_compute_included_sections(request),
            document_titles=[d.title for d in ctx.documents],
            ai_summary_text=_final_summary_text(ctx.ai_summary),
            patient_notes_text=(
                request.patient_notes_text if request.include_patient_notes else None
            ),
        )

    # -- PDF generation ---------------------------------------------------------
    async def generate_pdf(
        self, *, patient_id: uuid.UUID, request: HealthReportRequest
    ) -> bytes:
        ctx = await self._resolve_context(patient_id=patient_id, request=request)
        structured_data = self._build_structured_data(request=request, ctx=ctx)
        generator = get_pdf_generator()
        return await generator.generate_health_summary_pdf(structured_data=structured_data)

    @staticmethod
    def build_filename() -> str:
        # Never derived from any internal id -- just today's date, matching
        # the "no internal IDs in the filename" requirement.
        return f"health-summary-{date.today().isoformat()}.pdf"

    # -- share ------------------------------------------------------------------
    async def share(
        self,
        *,
        patient_id: uuid.UUID,
        request: HealthReportRequest,
        patient_email: str | None = None,
    ) -> EmailLog:
        if request.doctor_contact_id is None:
            raise ValidationAppError("Select a doctor to share this report with.")

        ctx = await self._resolve_context(patient_id=patient_id, request=request)
        assert ctx.doctor is not None  # guaranteed by _resolve_context given the id above
        if not ctx.doctor.email:
            raise ValidationAppError("This doctor contact has no email address on file.")

        structured_data = self._build_structured_data(request=request, ctx=ctx)
        generator = get_pdf_generator()
        pdf_bytes = await generator.generate_health_summary_pdf(structured_data=structured_data)
        pdf_filename = self.build_filename()
        report_name = f"CareQuill Health Summary — {date.today().isoformat()}"

        appointment_display = None
        if ctx.appointment:
            appointment_display = ctx.appointment.appointment_date.isoformat()
            if ctx.appointment.appointment_time:
                appointment_display += f" at {ctx.appointment.appointment_time.strftime('%H:%M')}"

        html_body, text_body = render_health_report_email(
            doctor_name=ctx.doctor.name,
            patient_name=ctx.patient_name,
            appointment_date_display=appointment_display,
            document_titles=[d.title for d in ctx.documents],
        )

        attachments: list[tuple[str, bytes, str]] = [(pdf_filename, pdf_bytes, "application/pdf")]
        for document in ctx.documents:
            try:
                content = await self.storage.read(storage_path=document.storage_path)
            except FileNotFoundError as exc:
                raise NotFoundError(
                    f"A selected document ('{document.title}') could not be found in storage."
                ) from exc
            # `original_filename` is already sanitized (see
            # app.utils.files.sanitize_filename) -- never the internal
            # `stored_filename`/on-disk path.
            attachments.append((document.original_filename, content, document.mime_type))

        message = EmailMessage(
            to=ctx.doctor.email,
            subject=report_name,
            html_body=html_body,
            text_body=text_body,
            attachments=attachments,
            reply_to=patient_email,
        )

        sender = get_email_sender()
        send_result = await sender.send(message)

        included_sections = _compute_included_sections(request)
        email_log = await self.email_logs.create(
            patient_id=patient_id,
            appointment_id=ctx.appointment.id if ctx.appointment else None,
            doctor_email=ctx.doctor.email,
            doctor_name=ctx.doctor.name,
            appointment_date=ctx.appointment.appointment_date if ctx.appointment else None,
            appointment_reason=ctx.appointment.reason if ctx.appointment else None,
            subject=report_name,
            report_name=report_name,
            included_sections=included_sections,
            status="sent" if send_result.success else "failed",
            error_message=None if send_result.success else send_result.error_message,
            sent_at=datetime.now(UTC) if send_result.success else None,
        )

        if send_result.success:
            await self.audit.record(
                user_id=patient_id,
                event_type="report_share",
                resource_type="email_log",
                resource_id=email_log.id,
            )
            await self.notifications.notify(
                patient_id=patient_id,
                type="report_shared",
                title="Health report shared",
                body=f"Your health summary was sent to Dr. {ctx.doctor.name}.",
                related_resource_id=email_log.id,
            )
        else:
            await self.notifications.notify(
                patient_id=patient_id,
                type="email_failure",
                title="Health report delivery failed",
                body=f"We couldn't send your health summary to Dr. {ctx.doctor.name}.",
                related_resource_id=email_log.id,
            )

        return email_log

    # -- shared context resolution ------------------------------------------------
    async def _resolve_context(
        self, *, patient_id: uuid.UUID, request: HealthReportRequest
    ) -> _ReportContext:
        ctx = _ReportContext()

        if request.doctor_contact_id is not None:
            doctor = await self.doctors.get_by_id_for_patient(
                request.doctor_contact_id, patient_id
            )
            if doctor is None:
                raise NotFoundError("Doctor contact not found.")
            ctx.doctor = doctor

        if request.appointment_id is not None:
            appointment = await self.appointments.get_by_id_for_patient(
                request.appointment_id, patient_id
            )
            if appointment is None:
                raise NotFoundError("Appointment not found.")
            ctx.appointment = appointment

        if request.ai_summary_id is not None:
            summary = await self.ai_summaries.get_by_id_for_patient(
                request.ai_summary_id, patient_id
            )
            if summary is None:
                raise NotFoundError("AI summary not found.")
            if summary.status not in _SHAREABLE_AI_SUMMARY_STATUSES:
                raise ValidationAppError(
                    "Only a reviewed AI summary can be included in a health report. "
                    f"This summary is {summary.status}."
                )
            ctx.ai_summary = summary

        if request.include_ai_summary and ctx.ai_summary is None:
            raise ValidationAppError(
                "Select a reviewed AI summary (ai_summary_id) to include the AI summary section."
            )

        for document_id in request.document_ids:
            document = await self.documents.get_by_id_for_patient(document_id, patient_id)
            if document is None:
                raise NotFoundError("One or more selected documents were not found.")
            ctx.documents.append(document)

        if request.include_conditions:
            ctx.conditions = await self.conditions.list_for_patient(patient_id)
        if request.include_allergies:
            ctx.allergies = await self.allergies.list_for_patient(patient_id)
        if request.include_medications:
            ctx.medications = await self.medications.list_active_for_patient(patient_id)
        if request.include_timeline:
            entries = await self.timeline.get_timeline(patient_id=patient_id)
            ctx.timeline_entries = entries[:_TIMELINE_EXCERPT_LIMIT]

        profile = await self.health_profiles.get_by_user_id(patient_id)
        if profile is not None:
            ctx.patient_name = f"{profile.first_name} {profile.last_name}".strip() or "Patient"
            ctx.patient_info = {
                "name": ctx.patient_name,
                "date_of_birth": (
                    profile.date_of_birth.isoformat() if profile.date_of_birth else None
                ),
                "gender": profile.gender,
                "blood_group": profile.blood_group,
            }
        else:
            ctx.patient_info = {"name": ctx.patient_name}

        return ctx

    def _build_structured_data(
        self, *, request: HealthReportRequest, ctx: _ReportContext
    ) -> dict:
        data: dict = {
            "patient_info": ctx.patient_info,
            "report_date": date.today().isoformat(),
            "appointment": None,
            "ai_summary_text": None,
            "patient_notes_text": None,
        }

        if ctx.appointment:
            data["appointment"] = {
                "date": ctx.appointment.appointment_date.isoformat(),
                "time": (
                    ctx.appointment.appointment_time.strftime("%H:%M")
                    if ctx.appointment.appointment_time
                    else None
                ),
                "reason": ctx.appointment.reason,
                "doctor_name": ctx.doctor.name if ctx.doctor else None,
            }

        if request.include_conditions:
            data["conditions"] = [
                {
                    "name": c.name,
                    "status": c.status,
                    "diagnosed_date": c.diagnosed_date.isoformat() if c.diagnosed_date else None,
                }
                for c in ctx.conditions
            ]

        if request.include_allergies:
            data["allergies"] = [
                {"name": a.name, "severity": a.severity, "reaction": a.reaction}
                for a in ctx.allergies
            ]

        if request.include_medications:
            data["medications"] = [
                {
                    "name": m.name,
                    "dosage": m.dosage,
                    "frequency": m.frequency,
                    "instructions": m.instructions,
                }
                for m in ctx.medications
            ]

        if request.include_timeline:
            data["timeline"] = [
                {
                    "date": e.date.isoformat(),
                    "type": e.type,
                    "title": e.title,
                    "detail": e.detail,
                }
                for e in ctx.timeline_entries
            ]

        if ctx.documents:
            data["documents"] = [
                {"title": d.title, "category": d.category} for d in ctx.documents
            ]

        if request.include_ai_summary:
            data["ai_summary_text"] = _final_summary_text(ctx.ai_summary)

        if request.include_patient_notes:
            data["patient_notes_text"] = request.patient_notes_text

        return data


def _final_summary_text(summary: AISummary | None) -> str | None:
    if summary is None:
        return None
    # Same rule as AISummaryService.share: once the patient has edited it,
    # the edited version is what they approved -- never the raw AI draft.
    return summary.edited_summary_text or summary.summary_text


def _compute_included_sections(request: HealthReportRequest) -> list[str]:
    sections = []
    if request.include_conditions:
        sections.append("conditions")
    if request.include_allergies:
        sections.append("allergies")
    if request.include_medications:
        sections.append("medications")
    if request.include_timeline:
        sections.append("timeline")
    if request.include_patient_notes:
        sections.append("patient_notes")
    if request.include_ai_summary:
        sections.append("ai_summary")
    if request.document_ids:
        sections.append("documents")
    if request.appointment_id:
        sections.append("appointment")
    return sections
