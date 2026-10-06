
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard import DashboardResponse, NextAppointmentSummary
from app.services.health_profile_service import HealthProfileService


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DashboardRepository(session)
        self.health_profile_service = HealthProfileService(session)

    async def get_dashboard(self, *, user: User) -> DashboardResponse:
        profile = await self.health_profile_service.get(user_id=user.id)
        completion = HealthProfileService.completion_percent(profile)

        next_appointment_row = await self.repo.get_next_appointment(user.id)
        counts = await self.repo.get_counts(user.id)
        reminders_due_today = await self.repo.count_reminders_due_today(user.id)

        notifications: list[str] = []
        if completion < 100:
            notifications.append("Complete your health profile to get the most out of MedQueue AI.")
        if not user.is_verified:
            notifications.append("Please verify your email address.")

        display_name = profile.first_name if profile else user.email.split("@")[0]

        return DashboardResponse(
            welcome_message=f"Welcome back, {display_name}!",
            profile_completion_percent=completion,
            has_health_profile=profile is not None,
            next_appointment=(
                NextAppointmentSummary(
                    id=next_appointment_row[0].id,
                    appointment_date=next_appointment_row[0].appointment_date.isoformat(),
                    reason=next_appointment_row[0].reason,
                    doctor_name=next_appointment_row[1],
                )
                if next_appointment_row
                else None
            ),
            active_medications_count=counts.active_medications,
            recent_documents_count=counts.documents,
            reminders_due_today_count=reminders_due_today,
            health_snapshot_status="up_to_date" if counts.has_snapshot else "not_generated",
            latest_ai_summary_status=counts.latest_ai_summary_status,
            notifications=notifications,
        )
