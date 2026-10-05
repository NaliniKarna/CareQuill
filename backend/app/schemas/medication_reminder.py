import re
import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

_VALID_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
_DAYS_PATTERN = re.compile(r"^(daily|[a-z]{3}(,[a-z]{3})*)$")


def _validate_days_of_week(value: str) -> str:
    normalized = value.strip().lower()
    if normalized == "daily":
        return normalized
    if not _DAYS_PATTERN.match(normalized):
        raise ValueError(
            'days_of_week must be "daily" or a comma-separated list like "mon,wed,fri".'
        )
    days = normalized.split(",")
    invalid = [d for d in days if d not in _VALID_DAYS]
    if invalid:
        raise ValueError(f"Invalid day(s): {', '.join(invalid)}. Use mon,tue,wed,thu,fri,sat,sun.")
    return normalized


class MedicationReminderBase(BaseModel):
    reminder_time: time
    days_of_week: str = Field(min_length=1, max_length=50)
    is_enabled: bool = True
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("days_of_week")
    @classmethod
    def _check_days(cls, v: str) -> str:
        return _validate_days_of_week(v)


class MedicationReminderCreate(MedicationReminderBase):
    pass


class MedicationReminderUpdate(BaseModel):
    reminder_time: time | None = None
    days_of_week: str | None = Field(default=None, min_length=1, max_length=50)
    is_enabled: bool | None = None
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("days_of_week")
    @classmethod
    def _check_days(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_days_of_week(v)


class MedicationReminderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    medication_id: uuid.UUID
    patient_id: uuid.UUID
    reminder_time: time
    days_of_week: str
    is_enabled: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
