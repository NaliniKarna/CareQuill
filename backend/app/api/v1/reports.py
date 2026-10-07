import io
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.db import get_db
from app.models.user import User
from app.schemas.ai_summary import EmailLogRead
from app.schemas.health_report import HealthReportPreview, HealthReportRequest
from app.schemas.report_share_link import (
    ReportShareLinkCreate,
    ReportShareLinkCreated,
    ReportShareLinkRead,
)
from app.services.health_report_service import HealthReportService
from app.services.report_share_link_service import ReportShareLinkService, to_read

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/preview", response_model=HealthReportPreview)
async def preview_report(
    payload: HealthReportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Returns exactly what would be sent (doctor, appointment, sections,
    document titles, AI summary text) -- generates no PDF and sends
    nothing."""
    service = HealthReportService(session)
    return await service.preview(patient_id=current_user.id, request=payload)


@router.post("/generate")
async def generate_report_pdf(
    payload: HealthReportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Generates the health-report PDF for the patient to download/review
    before sharing. Does not send anything."""
    service = HealthReportService(session)
    pdf_bytes = await service.generate_pdf(patient_id=current_user.id, request=payload)
    filename = service.build_filename()
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@router.post("/share", response_model=EmailLogRead)
async def share_report(
    payload: HealthReportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """The patient's explicit confirmation to send: generates the PDF and
    emails it (plus any selected documents) to the chosen doctor contact,
    then logs the result. This endpoint IS the confirmation -- nothing is
    ever sent by /preview or /generate."""
    service = HealthReportService(session)
    email_log = await service.share(
        patient_id=current_user.id, request=payload, patient_email=current_user.email
    )
    return EmailLogRead.model_validate(email_log)


# ---------------------------------------------------------------------------
# QR-code / link sharing
# ---------------------------------------------------------------------------
@router.post("/share-links", response_model=ReportShareLinkCreated, status_code=201)
async def create_share_link(
    payload: ReportShareLinkCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Creates a time-limited link (shown as a QR code) to this report and
    the selected documents. The URL is returned only once."""
    link, url = await ReportShareLinkService(session).create(
        patient_id=current_user.id, data=payload
    )
    return ReportShareLinkCreated(**to_read(link).model_dump(), url=url)


@router.get("/share-links", response_model=list[ReportShareLinkRead])
async def list_share_links(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    links = await ReportShareLinkService(session).list(patient_id=current_user.id)
    return [to_read(link) for link in links]


@router.post("/share-links/{link_id}/revoke", response_model=ReportShareLinkRead)
async def revoke_share_link(
    link_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Stops the link working immediately and deletes its report snapshot."""
    link = await ReportShareLinkService(session).revoke(
        patient_id=current_user.id, link_id=link_id
    )
    return to_read(link)
