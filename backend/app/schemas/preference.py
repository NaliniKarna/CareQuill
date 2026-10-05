from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationPrefs(BaseModel):
    appointment_reminders: bool = True
    medication_reminders: bool = True
    ai_summary_ready: bool = True
    document_processed: bool = True
    report_shared: bool = True
    email_failures: bool = True


class UserPreferenceUpdate(BaseModel):
    """All fields optional -- PUT applies a partial update (only fields the
    patient actually changed) rather than requiring the whole settings
    payload every time."""

    notification_prefs: NotificationPrefs | None = None
    data_sharing_consent: bool | None = None


class UserPreferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_prefs: NotificationPrefs
    data_sharing_consent: bool
    created_at: datetime
    updated_at: datetime
