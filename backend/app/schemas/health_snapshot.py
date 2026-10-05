import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class HealthSnapshotVersionRead(BaseModel):
    """Lightweight listing entry -- no `snapshot_data`, to keep the list
    endpoint cheap."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: int
    created_at: datetime


class HealthSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    version: int
    snapshot_data: dict
    created_at: datetime
