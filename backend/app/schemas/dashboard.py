import uuid

from pydantic import BaseModel


class NextAppointmentSummary(BaseModel):
    id: uuid.UUID
    appointment_date: str
    reason: str | None
    doctor_name: str | None


class DashboardResponse(BaseModel):
    welcome_message: str
    profile_completion_percent: int
    has_health_profile: bool
    next_appointment: NextAppointmentSummary | None
    active_medications_count: int
    recent_documents_count: int
    reminders_due_today_count: int
    health_snapshot_status: str  # "not_generated" | "up_to_date" | "stale"
    latest_ai_summary_status: str | None  # None | "pending_review" | "reviewed" | "shared"
    notifications: list[str]
