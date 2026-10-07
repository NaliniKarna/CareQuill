"""
Request/response shapes for the patient-configured health report
(preview / generate-PDF / share-by-email). See
`app.services.health_report_service` for why `preview`, `generate_pdf` and
`share` all take the exact same request shape.
"""
import uuid
from datetime import date

from pydantic import BaseModel, Field


class HealthReportRequest(BaseModel):
    # Required only for /reports/share (validated in the service, not here,
    # since the same shape is also used for /reports/preview and
    # /reports/generate, which don't need a doctor).
    doctor_contact_id: uuid.UUID | None = None
    appointment_id: uuid.UUID | None = None
    ai_summary_id: uuid.UUID | None = None
    # Explicit opt-in list -- never "all documents" by default.
    document_ids: list[uuid.UUID] = Field(default_factory=list)

    include_conditions: bool = False
    include_allergies: bool = False
    include_medications: bool = False
    include_timeline: bool = False
    include_patient_notes: bool = False
    include_ai_summary: bool = False

    # The actual freeform text for the "patient notes" section, only used
    # when include_patient_notes is true.
    patient_notes_text: str | None = Field(default=None, max_length=4000)


class ReportDocumentInfo(BaseModel):
    title: str
    original_filename: str
    mime_type: str
    file_size: int


class HealthReportPreview(BaseModel):
    """Exactly what the patient will see before they confirm sharing --
    never a PDF, never sent anywhere."""

    doctor_name: str | None
    doctor_email: str | None
    appointment_date: date | None
    appointment_reason: str | None
    included_sections: list[str]
    document_titles: list[str]
    # The selected documents, attached as the original files when shared.
    documents: list[ReportDocumentInfo] = Field(default_factory=list)
    attachments_total_bytes: int = 0
    max_email_attachments_bytes: int = 0
    ai_summary_text: str | None
    patient_notes_text: str | None
