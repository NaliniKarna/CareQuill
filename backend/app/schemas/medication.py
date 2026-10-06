import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MedicationBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dosage: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    instructions: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _validate_date_order(self) -> "MedicationBase":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date.")
        return self


class MedicationCreate(MedicationBase):
    is_active: bool = True
    # Set when the patient is adding this after reviewing an AI/OCR
    # suggestion from one of their own documents (verified server-side).
    source_document_id: uuid.UUID | None = None


class MedicationUpdate(MedicationBase):
    """Deliberately excludes `is_active` -- toggling active state goes
    through the dedicated /activate and /deactivate endpoints, not this
    generic update, per the product spec."""


class MedicationRead(MedicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    source: str = "manual"
    source_document_id: uuid.UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
