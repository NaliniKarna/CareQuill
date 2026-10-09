import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.phone import PhoneNumber


class DoctorContactBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    specialization: str | None = Field(default=None, max_length=150)
    clinic_name: str | None = Field(default=None, max_length=200)


class _DoctorContactWrite(DoctorContactBase):
    phone: PhoneNumber = None


class DoctorContactCreate(_DoctorContactWrite):
    pass


class DoctorContactUpdate(_DoctorContactWrite):
    pass


class DoctorContactRead(DoctorContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
