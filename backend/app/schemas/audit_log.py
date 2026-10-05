import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    resource_type: str | None
    resource_id: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
    limit: int
    offset: int
