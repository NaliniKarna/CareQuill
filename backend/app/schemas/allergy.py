import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AllergySeverity = Literal["mild", "moderate", "severe"]


class AllergyBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    severity: AllergySeverity | None = None
    reaction: str | None = Field(default=None, max_length=500)
    notes: str | None = None


class AllergyCreate(AllergyBase):
    pass


class AllergyUpdate(AllergyBase):
    pass


class AllergyRead(AllergyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
