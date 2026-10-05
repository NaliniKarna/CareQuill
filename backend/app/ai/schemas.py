"""
Pydantic-validated shape for AI-generated summaries -- this is the actual
hallucination-control gate. `AISummaryService` never persists, marks
reviewed, or shares anything a provider returns until it parses cleanly
through `StructuredAISummary`; on `ValidationError` (or a JSON decode
failure caught upstream in `app.ai.json_utils`) the service retries once
with a stricter prompt, then raises `AIGenerationError` rather than ever
storing malformed output or fabricating a fallback summary in code.

The field shape matches the JSON contract given to the model in
`app.ai.prompt.build_prompt` exactly.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.ai.prompt import REQUIRED_SUMMARY_PREFIX


class StructuredAISummary(BaseModel):
    summary: str = Field(min_length=1)
    verified_conditions: list[str] = Field(default_factory=list)
    verified_medications: list[str] = Field(default_factory=list)
    verified_allergies: list[str] = Field(default_factory=list)
    recent_events: list[str] = Field(default_factory=list)
    patient_concerns: str | None = None
    ai_extracted_notes: list[str] = Field(default_factory=list)
    unavailable: list[str] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def _summary_has_safety_prefix(cls, value: str) -> str:
        if not value.strip().startswith(REQUIRED_SUMMARY_PREFIX):
            raise ValueError(
                "summary must start with the required safety-disclosure "
                f"prefix: {REQUIRED_SUMMARY_PREFIX!r}"
            )
        return value
