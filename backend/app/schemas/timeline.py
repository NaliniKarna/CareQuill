import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TimelineEntryType = Literal[
    "condition", "medication", "document", "appointment", "note", "ai_extracted"
]
TimelineTag = Literal["VERIFIED", "PATIENT_PROVIDED", "AI_EXTRACTED", "UNVERIFIED"]


class TimelineEntry(BaseModel):
    date: date
    type: TimelineEntryType
    title: str
    detail: str | None
    source_id: uuid.UUID
    tag: TimelineTag


class TimelineNoteCreate(BaseModel):
    note_text: str = Field(min_length=1)
    event_date: date


class TimelineNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    note_text: str
    event_date: date
    created_at: datetime
    updated_at: datetime
