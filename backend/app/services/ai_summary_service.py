"""
Business logic for AI-generated health summaries: generation (via the
configured `AIProvider`, with Pydantic-validated structured output and a
single safe retry against hallucination/malformed output), the patient
review workflow (edit -> confirm), and sharing a reviewed summary with a
doctor contact by email.

Hallucination control, concretely: `AIProvider.generate_summary` results are
NEVER trusted directly. They are parsed through
`app.ai.schemas.StructuredAISummary` before anything is persisted. If that
fails (malformed/non-JSON output, or output that doesn't match the required
shape), generation is retried exactly once with a stricter prompt
(`AISummaryRequest.strict_json_retry`); if the retry also fails validation,
`AIGenerationError` is raised and nothing is stored -- this code never
fabricates a fallback summary itself.

Only `HealthSnapshotService.get_latest()` (verified, patient-confirmed
structured data) is ever treated as verified input to the prompt. Document
extractions the patient opts to include are passed through clearly labeled
as AI-extracted/unverified context and are never merged into the verified
section (see `app.ai.prompt`).
"""
from __future__ import annotations

import html
import uuid
from dataclasses import replace
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import get_ai_provider
from app.ai.interface import AIProvider, AISummaryRequest, AISummaryResult
from app.ai.json_utils import extract_json_object
from app.ai.schemas import StructuredAISummary
from app.core.config import settings
from app.core.exceptions import AIGenerationError, ConflictError, NotFoundError, ValidationAppError
from app.core.logging import logger
from app.email.factory import get_email_sender
from app.email.interface import EmailMessage
from app.models.ai_summary import AISummary
from app.models.email_log import EmailLog
from app.repositories.ai_summary_repository import AISummaryRepository
from app.repositories.doctor_contact_repository import DoctorContactRepository
from app.repositories.document_extraction_repository import DocumentExtractionRepository
from app.repositories.email_log_repository import EmailLogRepository
from app.repositories.health_profile_repository import HealthProfileRepository
from app.repositories.medical_document_repository import MedicalDocumentRepository
from app.schemas.ai_summary import AISummaryGenerateRequest
from app.services.audit_service import AuditService
from app.services.health_snapshot_service import HealthSnapshotService
from app.services.notification_service import NotificationService
from app.services.timeline_service import TimelineService

_RECENT_TIMELINE_LIMIT = 20

_STATUS_PENDING_REVIEW = "pending_review"
_STATUS_REVIEWED = "reviewed"
_STATUS_SHARED = "shared"
_STATUS_OUTDATED = "outdated"

_EDITABLE_STATUSES = (_STATUS_PENDING_REVIEW, _STATUS_REVIEWED)
_SHAREABLE_STATUSES = (_STATUS_REVIEWED, _STATUS_SHARED)


class AISummaryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AISummaryRepository(session)
        self.snapshots = HealthSnapshotService(session)
        self.timeline = TimelineService(session)
        self.extractions = DocumentExtractionRepository(session)
        self.documents = MedicalDocumentRepository(session)
        self.doctors = DoctorContactRepository(session)
        self.email_logs = EmailLogRepository(session)
        self.audit = AuditService(session)
        self.notifications = NotificationService(session)

    # -- generation -----------------------------------------------------

    async def generate(
        self, *, patient_id: uuid.UUID, data: AISummaryGenerateRequest
    ) -> AISummary:
        provider = get_ai_provider()
        if not await provider.is_available():
            status = await provider.status()
            raise ValidationAppError(
                "AI summary generation isn't enabled for this deployment. "
                + (status.detail or "Ask an administrator to enable and configure an AI provider.")
            )

        snapshot = await self.snapshots.get_latest(patient_id=patient_id)
        if snapshot is None:
            raise ValidationAppError(
                "Generate a health snapshot first, then generate an AI "
                "summary from it."
            )

        document_extractions = await self._resolve_document_extractions(
            patient_id=patient_id, include_document_ids=data.include_document_ids
        )
        timeline_entries = await self.timeline.get_timeline(patient_id=patient_id)

        request = AISummaryRequest(
            patient_id=str(patient_id),
            snapshot_data=snapshot.snapshot_data,
            prompt_version=settings.ai_prompt_version,
            patient_concerns=data.patient_concerns,
            document_extractions=document_extractions,
            timeline_entries=[
                entry.model_dump(mode="json")
                for entry in timeline_entries[:_RECENT_TIMELINE_LIMIT]
            ],
        )

        structured, result = await self._generate_validated(provider, request)

        summary = await self.repo.create(
            patient_id=patient_id,
            health_snapshot_id=snapshot.id,
            summary_text=structured.summary,
            edited_summary_text=None,
            structured_summary=structured.model_dump(),
            model_name=result.model_name,
            prompt_version=request.prompt_version,
            status=_STATUS_PENDING_REVIEW,
        )
        await self.audit.record(
            user_id=patient_id,
            event_type="ai_summary_generate",
            resource_type="ai_summary",
            resource_id=summary.id,
        )
        await self.notifications.notify(
            patient_id=patient_id,
            type="ai_summary_ready",
            title="AI summary ready for review",
            body="A new AI-assisted health summary is ready for you to review.",
            related_resource_id=summary.id,
        )
        return summary

    async def _resolve_document_extractions(
        self, *, patient_id: uuid.UUID, include_document_ids: list[uuid.UUID] | None
    ) -> list[dict]:
        if not include_document_ids:
            return []

        context: list[dict] = []
        for document_id in include_document_ids:
            # Ownership check first -- another IDOR angle: a patient must
            # never be able to pull another patient's document content into
            # their own AI summary prompt.
            document = await self.documents.get_by_id_for_patient(document_id, patient_id)
            if document is None:
                raise NotFoundError("One or more selected documents were not found.")

            extraction = await self.extractions.get_by_document_id(document.id)
            if extraction is None or not extraction.extracted_data:
                continue
            context.append(
                {
                    "document_id": str(document.id),
                    "document_title": document.title,
                    "extraction_status": extraction.status,
                    "extracted_data": extraction.extracted_data,
                }
            )
        return context

    async def _generate_validated(
        self, provider: AIProvider, request: AISummaryRequest
    ) -> tuple[StructuredAISummary, AISummaryResult]:
        result = await self._call_provider(provider, request)
        structured = self._parse_structured(result)
        if structured is not None:
            return structured, result

        logger.warning(
            "AI summary generation returned unparseable/invalid structured "
            "output for patient_id=%s; retrying once with a stricter prompt.",
            request.patient_id,
        )
        retry_request = replace(request, strict_json_retry=True)
        retry_result = await self._call_provider(provider, retry_request)
        structured = self._parse_structured(retry_result)
        if structured is not None:
            return structured, retry_result

        raise AIGenerationError(
            "The AI provider did not return a valid structured summary, "
            "even after a retry. Please try again later."
        )

    async def _call_provider(
        self, provider: AIProvider, request: AISummaryRequest
    ) -> AISummaryResult:
        try:
            return await provider.generate_summary(request)
        except AIGenerationError:
            raise
        except Exception as exc:
            logger.exception("AI provider call failed during summary generation.")
            raise AIGenerationError(
                "The AI provider failed to generate a summary. Please try again later."
            ) from exc

    def _parse_structured(self, result: AISummaryResult) -> StructuredAISummary | None:
        payload = result.structured_summary
        if payload is None:
            payload = extract_json_object(result.summary_text)
        if payload is None:
            return None
        try:
            return StructuredAISummary.model_validate(payload)
        except ValidationError:
            return None

    # -- listing / review -------------------------------------------------

    async def list(self, *, patient_id: uuid.UUID) -> list[AISummary]:
        return await self.repo.list_for_patient(patient_id)

    async def get(self, *, patient_id: uuid.UUID, summary_id: uuid.UUID) -> AISummary:
        summary = await self.repo.get_by_id_for_patient(summary_id, patient_id)
        if summary is None:
            raise NotFoundError("AI summary not found.")
        return summary

    async def save_edit(
        self, *, patient_id: uuid.UUID, summary_id: uuid.UUID, edited_summary_text: str
    ) -> AISummary:
        summary = await self.get(patient_id=patient_id, summary_id=summary_id)
        if summary.status not in _EDITABLE_STATUSES:
            raise ConflictError(
                f"This summary is {summary.status} and can no longer be edited."
            )
        updated = await self.repo.update(summary, edited_summary_text=edited_summary_text)
        await self.audit.record(
            user_id=patient_id,
            event_type="ai_summary_edit",
            resource_type="ai_summary",
            resource_id=summary_id,
        )
        return updated

    async def confirm_review(self, *, patient_id: uuid.UUID, summary_id: uuid.UUID) -> AISummary:
        summary = await self.get(patient_id=patient_id, summary_id=summary_id)
        if summary.status in (_STATUS_SHARED, _STATUS_OUTDATED):
            raise ConflictError(
                f"This summary is {summary.status} and cannot be marked reviewed."
            )
        return await self.repo.update(
            summary, status=_STATUS_REVIEWED, reviewed_at=datetime.now(UTC)
        )

    # -- sharing ----------------------------------------------------------

    async def share(
        self,
        *,
        patient_id: uuid.UUID,
        summary_id: uuid.UUID,
        doctor_contact_id: uuid.UUID,
        patient_email: str | None = None,
    ) -> EmailLog:
        summary = await self.get(patient_id=patient_id, summary_id=summary_id)
        if summary.status not in _SHAREABLE_STATUSES:
            raise ConflictError(
                f"This summary is {summary.status}. It must be reviewed and "
                "confirmed before it can be shared."
            )

        doctor = await self.doctors.get_by_id_for_patient(doctor_contact_id, patient_id)
        if doctor is None:
            raise NotFoundError("Doctor contact not found.")
        if not doctor.email:
            raise ValidationAppError("This doctor contact has no email address on file.")

        # Never send the raw unedited AI draft once the patient has edited
        # it -- the edited version is what the patient actually approved.
        final_text = summary.edited_summary_text or summary.summary_text
        subject = "Patient health summary"
        profile = await HealthProfileRepository(self.session).get_by_user_id(patient_id)
        patient_name = (
            f"{profile.first_name} {profile.last_name}".strip() if profile else ""
        ) or "a patient"
        sender_line = f"Shared by {patient_name}" + (
            f" ({patient_email}) - reply to this email to reach them." if patient_email else "."
        )
        message = EmailMessage(
            to=doctor.email,
            subject=subject,
            html_body=f"<p><em>{html.escape(sender_line)}</em></p>" + _render_html_body(final_text),
            text_body=f"{sender_line}\n\n{final_text}",
            reply_to=patient_email,
        )

        sender = get_email_sender()
        send_result = await sender.send(message)

        email_log = await self.email_logs.create(
            patient_id=patient_id,
            doctor_email=doctor.email,
            doctor_name=doctor.name,
            subject=subject,
            report_name=subject,
            status="sent" if send_result.success else "failed",
            error_message=None if send_result.success else send_result.error_message,
            sent_at=datetime.now(UTC) if send_result.success else None,
        )

        if send_result.success:
            await self.repo.update(summary, status=_STATUS_SHARED)
        else:
            logger.warning(
                "Failed to email AI summary %s to doctor_contact_id=%s for "
                "patient_id=%s.",
                summary_id,
                doctor_contact_id,
                patient_id,
            )
            await self.notifications.notify(
                patient_id=patient_id,
                type="email_failure",
                title="AI summary delivery failed",
                body=f"We couldn't send your AI summary to Dr. {doctor.name}.",
                related_resource_id=email_log.id,
            )

        return email_log


def _render_html_body(text: str) -> str:
    escaped = html.escape(text)
    paragraphs = [p.strip() for p in escaped.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [escaped]
    return "".join(f"<p>{p.replace(chr(10), '<br/>')}</p>" for p in paragraphs)
