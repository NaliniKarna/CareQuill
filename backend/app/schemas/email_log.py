"""Schema for GET /api/v1/email-logs -- the patient's sharing history.

Deliberately excludes `included_sections`' full content and any document/
AI-summary text: this is a metadata-only history view (doctor, appointment,
sent date, status, report name), per the product spec."""
import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class EmailLogListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    doctor_name: str | None
    doctor_email: str
    appointment_date: date | None
    appointment_reason: str | None
    report_name: str | None
    status: str
    sent_at: datetime | None
    created_at: datetime
