import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AppointmentStatus = Literal["scheduled", "completed", "cancelled", "missed"]


class AppointmentCreate(BaseModel):
    doctor_contact_id: uuid.UUID | None = None
    appointment_date: date
    appointment_time: time | None = None
    reason: str | None = Field(default=None, max_length=500)
    notes: str | None = None

    @model_validator(mode="after")
    def _validate_future_date(self) -> "AppointmentCreate":
        if self.appointment_date < date.today():
            raise ValueError("A new appointment's date must be today or in the future.")
        return self


class AppointmentUpdate(BaseModel):
    """Deliberately excludes `status` -- status transitions go through the
    dedicated /cancel, /complete and /miss endpoints."""

    doctor_contact_id: uuid.UUID | None = None
    appointment_date: date | None = None
    appointment_time: time | None = None
    reason: str | None = Field(default=None, max_length=500)
    notes: str | None = None


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_contact_id: uuid.UUID | None
    appointment_date: date
    appointment_time: time | None
    reason: str | None
    notes: str | None
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime
