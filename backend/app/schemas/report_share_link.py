"""Shapes for QR-code / link sharing of a health report."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.health_report import HealthReportRequest


class ReportShareLinkCreate(BaseModel):
    report: HealthReportRequest
    # Upper bound is enforced in the service from settings.share_link_max_hours.
    expires_in_hours: int = Field(default=72, ge=1)


class ReportShareLinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipient_label: str | None
    report_name: str
    included_sections: list[str]
    document_count: int
    expires_at: datetime
    revoked_at: datetime | None
    view_count: int
    last_viewed_at: datetime | None
    created_at: datetime
    status: str  # active | expired | revoked


class ReportShareLinkCreated(ReportShareLinkRead):
    """Returned once, on creation. The secret URL is never shown again
    (only a hash of its token is stored)."""

    url: str


class SharedReportAccessRequest(BaseModel):
    # token_urlsafe(32) gives 43 characters.
    token: str = Field(min_length=20, max_length=128)


class SharedReportDocumentRequest(SharedReportAccessRequest):
    document_id: uuid.UUID


class SharedDocumentInfo(BaseModel):
    id: uuid.UUID
    title: str
    original_filename: str
    mime_type: str
    file_size: int


class SharedReportInfo(BaseModel):
    patient_name: str
    report_name: str
    recipient_label: str | None
    included_sections: list[str]
    created_at: datetime
    expires_at: datetime
    documents: list[SharedDocumentInfo]
