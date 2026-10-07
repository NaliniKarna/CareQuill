"""
Public (no login) access to a report the patient shared by QR code / link.

The secret token is sent in the JSON body, never in the URL, so it does not
end up in access logs. See `app.services.report_share_link_service`.
"""
import io
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.db import get_db
from app.core.rate_limit import shared_link_rate_limit
from app.schemas.report_share_link import (
    SharedReportAccessRequest,
    SharedReportDocumentRequest,
    SharedReportInfo,
)
from app.services.report_share_link_service import ReportShareLinkService, SharedFile

router = APIRouter(
    prefix="/public/shared-reports",
    tags=["shared-reports"],
    dependencies=[Depends(shared_link_rate_limit)],
)


def _file_response(file: SharedFile) -> StreamingResponse:
    # RFC 5987 encoding keeps non-ASCII filenames safe in the header.
    disposition = f"attachment; filename*=UTF-8''{quote(file.filename)}"
    return StreamingResponse(
        io.BytesIO(file.content),
        media_type=file.mime_type,
        headers={"Content-Disposition": disposition, "Cache-Control": "no-store"},
    )


@router.post("/info", response_model=SharedReportInfo)
async def shared_report_info(
    payload: SharedReportAccessRequest, session: AsyncSession = Depends(get_db)
):
    return await ReportShareLinkService(session).info(token=payload.token)


@router.post("/report")
async def shared_report_pdf(
    payload: SharedReportAccessRequest, session: AsyncSession = Depends(get_db)
):
    return _file_response(await ReportShareLinkService(session).read_report(token=payload.token))


@router.post("/document")
async def shared_report_document(
    payload: SharedReportDocumentRequest, session: AsyncSession = Depends(get_db)
):
    file = await ReportShareLinkService(session).read_document(
        token=payload.token, document_id=payload.document_id
    )
    return _file_response(file)
