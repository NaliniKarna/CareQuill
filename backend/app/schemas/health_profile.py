import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class HealthProfileBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=50)
    blood_group: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=500)
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)
    height: Decimal | None = Field(default=None, ge=0, le=999)
    weight: Decimal | None = Field(default=None, ge=0, le=999)


class HealthProfileUpsert(HealthProfileBase):
    pass


class HealthProfileRead(HealthProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
