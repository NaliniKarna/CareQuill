import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConditionStatus = Literal["active", "managed", "resolved"]


class MedicalConditionBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    diagnosed_date: date | None = None
    status: ConditionStatus | None = None
    notes: str | None = None


class MedicalConditionCreate(MedicalConditionBase):
    pass


class MedicalConditionUpdate(MedicalConditionBase):
    pass


class MedicalConditionRead(MedicalConditionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
