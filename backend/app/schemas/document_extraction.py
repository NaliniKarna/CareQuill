import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DocumentExtractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    raw_text: str | None
    confidence: float | None
    extracted_data: dict | None
    status: str
    created_at: datetime
    updated_at: datetime


class DocumentExtractionStatusUpdate(BaseModel):
    """Marks an extraction reviewed or dismissed. This is a review-state
    change ONLY -- it never writes into allergies/medications/conditions.
    The frontend flow is: patient reviews the suggested values here, then
    manually copies whichever ones they want into the normal Add
    Medication/Allergy/Condition forms, which POST to those resources'
    own create endpoints like any other manual entry. Do not "helpfully"
    add an auto-apply path here later -- that would violate the
    AI-suggestions-require-explicit-review rule."""

    status: Literal["reviewed", "dismissed"]


class ExplainedTerm(BaseModel):
    term: str
    meaning: str


class DocumentExplanationRead(BaseModel):
    explanation: str
    terms: list[ExplainedTerm]
    questions_for_doctor: list[str]
    model: str
