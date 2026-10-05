import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

NotificationType = Literal[
    "appointment_approaching",
    "medication_reminder",
    "ai_summary_ready",
    "document_processed",
    "report_shared",
    "email_failure",
]


class NotificationRead(BaseModel):
    id: uuid.UUID
    type: NotificationType
    title: str
    body: str
    is_read: bool
    related_resource_id: str | None
    created_at: datetime
    # True for a real, stored row (can be marked read); False for a
    # computed-on-read notification (appointment_approaching /
    # medication_reminder), which is always informational/unread and whose
    # `id`, though a real UUID, never matches a stored row.
    persisted: bool
