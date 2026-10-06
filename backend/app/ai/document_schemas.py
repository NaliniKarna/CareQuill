"""
Pydantic gates for the document-intelligence AI calls. Same principle as
`app.ai.schemas.StructuredAISummary`: a provider's JSON is untrusted text
until it parses through one of these models, and anything that fails to
parse is discarded (never "repaired" or invented in code).

None of these models has a field for a diagnosis, a finding, or treatment
advice -- the contract simply has nowhere to put one.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Literal prefix every plain-language explanation must start with, so it can
# never be mistaken for a clinician's interpretation.
EXPLANATION_PREFIX = (
    "AI-assisted plain-language explanation of what is written in this "
    "document. It is not medical advice or a diagnosis."
)


def _clean_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = " ".join(str(value).split())
        if item and item.lower() not in seen:
            seen.add(item.lower())
            out.append(item[:300])
    return out[:50]


class AIExtractedMedication(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    dosage: str | None = Field(default=None, max_length=60)
    frequency: str | None = Field(default=None, max_length=80)


class AIExtractedLabValue(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=40)
    unit: str | None = Field(default=None, max_length=40)
    range: str | None = Field(default=None, max_length=60)
    flag: str | None = Field(default=None, max_length=30)


class StructuredDocumentExtraction(BaseModel):
    """What the model is allowed to pull OUT of the document text. Every
    value must be something literally written in the document; the service
    additionally verifies that against the source text before keeping it."""

    document_type: str | None = Field(default=None, max_length=80)
    medications: list[AIExtractedMedication] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    procedures: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    lab_values: list[AIExtractedLabValue] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @field_validator(
        "conditions", "allergies", "procedures", "dates", "recommendations", mode="before"
    )
    @classmethod
    def _coerce_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return _clean_list([str(v) for v in value])  # type: ignore[attr-defined]


class TermMeaning(BaseModel):
    term: str = Field(min_length=1, max_length=120)
    meaning: str = Field(min_length=1, max_length=400)


class DocumentExplanation(BaseModel):
    explanation: str = Field(min_length=1, max_length=4000)
    terms: list[TermMeaning] = Field(default_factory=list)
    questions_for_doctor: list[str] = Field(default_factory=list)

    @field_validator("explanation")
    @classmethod
    def _has_disclaimer_prefix(cls, value: str) -> str:
        if not value.strip().startswith(EXPLANATION_PREFIX):
            raise ValueError(f"explanation must start with: {EXPLANATION_PREFIX!r}")
        return value

    @field_validator("questions_for_doctor", mode="before")
    @classmethod
    def _coerce_questions(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return _clean_list([str(v) for v in value])[:8]  # type: ignore[attr-defined]


ImageModality = Literal["xray", "mri", "ct", "ultrasound", "photo", "document_scan", "other"]


class ImageDescription(BaseModel):
    """DESCRIPTIVE metadata about an uploaded image only. Deliberately has no
    field for findings, abnormalities, impressions or diagnoses."""

    modality_guess: ImageModality | None = None
    body_region_guess: str | None = Field(default=None, max_length=80)
    view_or_orientation: str | None = Field(default=None, max_length=80)
    image_quality: Literal["good", "fair", "poor"] | None = None
    visible_text: list[str] = Field(default_factory=list)

    @field_validator("visible_text", mode="before")
    @classmethod
    def _coerce_text(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return _clean_list([str(v) for v in value])[:20]  # type: ignore[attr-defined]
