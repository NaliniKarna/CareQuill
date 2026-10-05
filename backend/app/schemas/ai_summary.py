import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AISummaryGenerateRequest(BaseModel):
    patient_concerns: str | None = Field(default=None, max_length=4000)
    include_document_ids: list[uuid.UUID] | None = None


class AISummaryEditRequest(BaseModel):
    edited_summary_text: str = Field(min_length=1)


class AISummaryShareRequest(BaseModel):
    doctor_contact_id: uuid.UUID


class AISummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    health_snapshot_id: uuid.UUID | None
    summary_text: str
    edited_summary_text: str | None
    structured_summary: dict | None
    model_name: str
    prompt_version: str
    status: str
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EmailLogRead(BaseModel):
    """Full detail returned right after a share/generate call (the patient's
    own action, in the same response). The list endpoint
    (`GET /api/v1/email-logs`) uses the narrower `EmailLogListItem` instead
    -- see `app.schemas.email_log`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    appointment_id: uuid.UUID | None
    doctor_email: str
    doctor_name: str | None
    subject: str
    report_name: str | None
    status: str
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime
