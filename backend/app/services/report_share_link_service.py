"""
QR-code / link sharing of a health report.

The patient configures a report exactly as for email sharing, then creates a
time-limited link. The QR code shown in the app encodes that link.

Security design:
 - The link carries a random 256-bit token. Only its SHA-256 hash is stored.
 - The token travels in the URL *fragment* (`/shared#<token>`). Browsers
   never send fragments to servers, so the token does not appear in server
   access logs or Referer headers. The public page reads it and posts it in
   a request body to the endpoints below.
 - Invalid, expired and revoked links all return the same 404, so the API
   does not reveal which tokens ever existed.
 - The PDF is generated once at creation (what the patient previewed) and
   the selected document ids are snapshotted. A document deleted later is no
   longer served.
 - Public access is rate limited per IP; every view is counted and shown to
   the patient, who can revoke the link at any time.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging import logger
from app.db.session import session_scope
from app.models.report_share_link import ReportShareLink
from app.repositories.medical_document_repository import MedicalDocumentRepository
from app.repositories.report_share_link_repository import ReportShareLinkRepository
from app.schemas.report_share_link import (
    ReportShareLinkCreate,
    ReportShareLinkRead,
    SharedDocumentInfo,
    SharedReportInfo,
)
from app.services.audit_service import AuditService
from app.services.health_report_service import HealthReportService
from app.storage.factory import get_storage_backend
from app.utils.names import doctor_display_name

_INVALID_LINK = "This link is invalid or has expired."


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def link_status(link: ReportShareLink, *, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    if link.revoked_at is not None:
        return "revoked"
    if link.expires_at <= now:
        return "expired"
    return "active"


def to_read(link: ReportShareLink) -> ReportShareLinkRead:
    return ReportShareLinkRead(
        id=link.id,
        recipient_label=link.recipient_label,
        report_name=link.report_name,
        included_sections=list(link.included_sections or []),
        document_count=len(link.document_ids or []),
        expires_at=link.expires_at,
        revoked_at=link.revoked_at,
        view_count=link.view_count,
        last_viewed_at=link.last_viewed_at,
        created_at=link.created_at,
        status=link_status(link),
    )


@dataclass
class SharedFile:
    content: bytes
    filename: str
    mime_type: str


class ReportShareLinkService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReportShareLinkRepository(session)
        self.documents = MedicalDocumentRepository(session)
        self.storage = get_storage_backend()
        self.audit = AuditService(session)

    # -- patient (authenticated) -------------------------------------------------
    async def create(
        self, *, patient_id: uuid.UUID, data: ReportShareLinkCreate
    ) -> tuple[ReportShareLink, str]:
        if data.expires_in_hours > settings.share_link_max_hours:
            raise ValidationAppError(
                f"A link can stay open for at most {settings.share_link_max_hours} hours."
            )
        request = data.report
        if not any(
            (
                request.include_conditions,
                request.include_allergies,
                request.include_medications,
                request.include_timeline,
                request.include_patient_notes,
                request.include_ai_summary,
                request.document_ids,
            )
        ):
            raise ValidationAppError(
                "Select at least one section or document to include in the report."
            )

        rendered = await HealthReportService(self.session).render(
            patient_id=patient_id, request=request
        )
        link_id = uuid.uuid4()
        token = secrets.token_urlsafe(32)
        storage_path = await self.storage.save(
            relative_path=f"shared-reports/{patient_id}/{link_id}.pdf",
            content=rendered.pdf_bytes,
        )
        try:
            link = await self.repo.create(
                id=link_id,
                patient_id=patient_id,
                token_hash=hash_token(token),
                recipient_label=(
                    doctor_display_name(rendered.doctor_name) if rendered.doctor_name else None
                ),
                patient_name=rendered.patient_name,
                report_name=f"CareQuill Health Summary — {date.today().isoformat()}",
                included_sections=rendered.included_sections,
                document_ids=[str(d.id) for d in rendered.documents],
                report_storage_path=storage_path,
                expires_at=datetime.now(UTC) + timedelta(hours=data.expires_in_hours),
            )
            await self.audit.record(
                user_id=patient_id,
                event_type="report_share_link_create",
                resource_type="report_share_link",
                resource_id=link.id,
            )
        except Exception:
            await self.storage.delete(storage_path=storage_path)
            raise
        url = f"{settings.frontend_base_url.rstrip('/')}/shared#{token}"
        return link, url

    async def list(self, *, patient_id: uuid.UUID) -> list[ReportShareLink]:
        return await self.repo.list_for_patient(patient_id)

    async def revoke(self, *, patient_id: uuid.UUID, link_id: uuid.UUID) -> ReportShareLink:
        link = await self.repo.get_by_id_for_patient(link_id, patient_id)
        if link is None:
            raise NotFoundError("Share link not found.")
        if link.revoked_at is None:
            link.revoked_at = datetime.now(UTC)
            await self._remove_snapshot(link)
            await self.session.flush()
            await self.audit.record(
                user_id=patient_id,
                event_type="report_share_link_revoke",
                resource_type="report_share_link",
                resource_id=link.id,
            )
        return link

    # -- public (token holder, no login) ---------------------------------------
    async def _active_link(self, token: str) -> ReportShareLink:
        link = await self.repo.get_by_token_hash(hash_token(token))
        if (
            link is None
            or link_status(link) != "active"
            or link.report_storage_path is None
        ):
            raise NotFoundError(_INVALID_LINK)
        return link

    async def info(self, *, token: str) -> SharedReportInfo:
        link = await self._active_link(token)
        link.view_count += 1
        link.last_viewed_at = datetime.now(UTC)
        await self.session.flush()
        documents: list[SharedDocumentInfo] = []
        for raw_id in link.document_ids or []:
            document = await self.documents.get_by_id_for_patient(
                uuid.UUID(raw_id), link.patient_id
            )
            if document is not None:
                documents.append(
                    SharedDocumentInfo(
                        id=document.id,
                        title=document.title,
                        original_filename=document.original_filename,
                        mime_type=document.mime_type,
                        file_size=document.file_size,
                    )
                )
        return SharedReportInfo(
            patient_name=link.patient_name,
            report_name=link.report_name,
            recipient_label=link.recipient_label,
            included_sections=list(link.included_sections or []),
            created_at=link.created_at,
            expires_at=link.expires_at,
            documents=documents,
        )

    async def read_report(self, *, token: str) -> SharedFile:
        link = await self._active_link(token)
        assert link.report_storage_path is not None  # checked in _active_link
        try:
            content = await self.storage.read(storage_path=link.report_storage_path)
        except FileNotFoundError as exc:
            raise NotFoundError(_INVALID_LINK) from exc
        filename = f"health-summary-{link.created_at.date().isoformat()}.pdf"
        return SharedFile(content=content, filename=filename, mime_type="application/pdf")

    async def read_document(self, *, token: str, document_id: uuid.UUID) -> SharedFile:
        link = await self._active_link(token)
        if str(document_id) not in (link.document_ids or []):
            raise NotFoundError("Document not found.")
        document = await self.documents.get_by_id_for_patient(document_id, link.patient_id)
        if document is None:
            raise NotFoundError("Document not found.")
        try:
            content = await self.storage.read(storage_path=document.storage_path)
        except FileNotFoundError as exc:
            raise NotFoundError("Document not found.") from exc
        return SharedFile(
            content=content, filename=document.original_filename, mime_type=document.mime_type
        )

    # -- housekeeping ---------------------------------------------------------
    async def _remove_snapshot(self, link: ReportShareLink) -> None:
        if link.report_storage_path is None:
            return
        try:
            await self.storage.delete(storage_path=link.report_storage_path)
        except Exception:  # noqa: BLE001 - the link is already unusable
            logger.exception("Could not remove a shared report snapshot.")
        link.report_storage_path = None


async def purge_expired_share_snapshots() -> int:
    """Deletes report PDFs of expired/revoked links. Runs at startup."""
    try:
        async with session_scope() as session:
            service = ReportShareLinkService(session)
            links = await service.repo.list_with_files_to_purge(now=datetime.now(UTC))
            for link in links:
                await service._remove_snapshot(link)
            return len(links)
    except Exception:
        logger.exception("Could not purge expired shared report files.")
        return 0
