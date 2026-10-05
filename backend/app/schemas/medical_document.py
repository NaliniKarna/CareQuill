import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentCategory = Literal[
    "prescription",
    "blood_test",
    "lab_report",
    "xray",
    "mri",
    "ct_scan",
    "discharge_summary",
    "vaccination",
    "referral",
    "other",
]


class MedicalDocumentUploadForm(BaseModel):
    """Validates the non-file multipart form fields for a document upload.
    The file itself is handled separately (streamed, size/type-checked)
    before this model is even relevant."""

    title: str = Field(min_length=1, max_length=200)
    category: DocumentCategory | None = None
    visit_date: date | None = None
    doctor_name: str | None = Field(default=None, max_length=200)
    hospital_name: str | None = Field(default=None, max_length=200)


class MedicalDocumentRead(BaseModel):
    """Deliberately excludes `storage_path` and `stored_filename` -- the
    physical location of a file must never appear in a JSON response. Use
    GET /documents/{id}/download to retrieve the file itself."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    title: str
    category: str | None
    original_filename: str
    mime_type: str
    file_size: int
    visit_date: date | None
    doctor_name: str | None
    hospital_name: str | None
    ocr_status: str
    processing_status: str
    created_at: datetime
    updated_at: datetime


class MedicalDocumentListResponse(BaseModel):
    items: list[MedicalDocumentRead]
    total: int
    limit: int
    offset: int
