import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JournalEntryBase(BaseModel):
    entry_date: date
    mood: int | None = Field(default=None, ge=1, le=5)
    title: str | None = Field(default=None, max_length=200)
    body: str = Field(min_length=1, max_length=10_000)

    @field_validator("body")
    @classmethod
    def _body_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Write something before saving.")
        return value

    @field_validator("title")
    @classmethod
    def _blank_title_is_none(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class JournalEntryCreate(JournalEntryBase):
    @field_validator("entry_date")
    @classmethod
    def _not_in_future(cls, value: date) -> date:
        # A day of slack covers time-zone differences between browser and server.
        if (value - date.today()).days > 1:
            raise ValueError("Journal entries cannot be dated in the future.")
        return value


class JournalEntryUpdate(JournalEntryCreate):
    pass


class JournalEntryRead(JournalEntryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class JournalListResponse(BaseModel):
    items: list[JournalEntryRead]
    total: int
