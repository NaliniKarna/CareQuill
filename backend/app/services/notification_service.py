"""
In-app notifications: two kinds, merged on read.

Persisted notifications (`Notification` rows) are created at the moment a
specific event happens -- AI summary generation completes, a document's OCR
pipeline finishes, a health report is shared, or an email send fails (see
`notify()` call sites in `ai_summary_service`, `document_processing_service`,
and `health_report_service`). They can be marked read.

Computed notifications (`appointment_approaching`, `medication_reminder`)
are deliberately NEVER persisted. "This appointment is now within 48
hours" and "this reminder is due today" are facts about the current time,
re-derived fresh on every call from live `Appointment`/`MedicationReminder`
rows -- persisting them would require a background job to keep them from
going stale or duplicating. They are always treated as unread/informational
(there is no read-state to store), `unread_only` always includes them, and
their `id` is a deterministic UUID (uuid5 of the source resource id) purely
so the frontend has a stable key -- it never matches a stored row, so
`PATCH .../read` on one always 404s.

Note: `Appointment.appointment_date`/`appointment_time` are plain
Date/Time columns with no timezone (the app never collects the patient's
timezone), so the "within 48 hours" comparison here is naive-datetime
arithmetic against the server clock, consistent with how appointments are
stored and displayed everywhere else in this codebase.
"""
from __future__ import annotations

import builtins  # used below to reference the builtin `list` unambiguously
import uuid
from datetime import UTC, datetime, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.medication_reminder_repository import MedicationReminderRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationRead

# Fixed namespace UUID (arbitrary, generated once) used to derive stable,
# deterministic ids for computed (never-persisted) notifications.
_COMPUTED_NAMESPACE = uuid.UUID("5b1f9a0e-9b1e-4f0a-9c3e-1f9a2b3c4d5e")
_APPROACHING_WINDOW = timedelta(hours=48)
_WEEKDAY_CODES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = NotificationRepository(session)
        self.appointments = AppointmentRepository(session)
        self.reminders = MedicationReminderRepository(session)

    # -- creation (called from other services at the moment an event happens)
    async def notify(
        self,
        *,
        patient_id: uuid.UUID,
        type: str,
        title: str,
        body: str,
        related_resource_id: uuid.UUID | str | None = None,
    ) -> Notification:
        return await self.repo.create(
            patient_id=patient_id,
            type=type,
            title=title,
            body=body,
            related_resource_id=(
                str(related_resource_id) if related_resource_id is not None else None
            ),
        )

    # -- reading -------------------------------------------------------------
    async def list(self, *, patient_id: uuid.UUID, unread_only: bool) -> list[NotificationRead]:
        persisted = await self.repo.list_for_patient(patient_id, unread_only=unread_only)
        results = [_from_persisted(n) for n in persisted]
        # Computed notifications are always considered unread/informational,
        # so they're included regardless of `unread_only`.
        results.extend(await self._computed(patient_id))
        results.sort(key=lambda n: n.created_at, reverse=True)
        return results

    async def mark_read(
        self, *, patient_id: uuid.UUID, notification_id: uuid.UUID
    ) -> NotificationRead:
        notification = await self.repo.get_by_id_for_patient(notification_id, patient_id)
        if notification is None:
            raise NotFoundError("Notification not found.")
        updated = await self.repo.mark_read(notification)
        return _from_persisted(updated)

    # -- computed-on-read ------------------------------------------------------
    # NOTE: annotated as `builtins.list[...]`, not bare `list[...]` -- this
    # class also defines a method named `list`, which (with
    # `from __future__ import annotations`) mypy would otherwise resolve
    # the annotation to instead of the builtin.
    async def _computed(self, patient_id: uuid.UUID) -> builtins.list[NotificationRead]:
        # `now_local` (naive) is compared against the naive Date/Time
        # appointment fields; `now_aware` (tz-aware) populates `created_at`
        # so these entries sort correctly alongside persisted rows, whose
        # `created_at` is always tz-aware.
        now_local = datetime.now()
        now_aware = datetime.now(UTC)
        entries: list[NotificationRead] = []

        upcoming = await self.appointments.list_for_patient(patient_id, filter="upcoming")
        for appt in upcoming:
            appt_dt = datetime.combine(appt.appointment_date, appt.appointment_time or time(0, 0))
            if now_local <= appt_dt <= now_local + _APPROACHING_WINDOW:
                when = appt.appointment_date.isoformat()
                if appt.appointment_time:
                    when += f" at {appt.appointment_time.strftime('%H:%M')}"
                body = f"You have an appointment on {when}."
                if appt.reason:
                    body += f" Reason: {appt.reason}"
                entries.append(
                    NotificationRead(
                        id=uuid.uuid5(_COMPUTED_NAMESPACE, f"appointment_approaching:{appt.id}"),
                        type="appointment_approaching",
                        title="Upcoming appointment",
                        body=body,
                        is_read=False,
                        related_resource_id=str(appt.id),
                        created_at=now_aware,
                        persisted=False,
                    )
                )

        today_code = _WEEKDAY_CODES[now_local.weekday()]
        reminders = await self.reminders.list_for_patient(patient_id)
        for reminder in reminders:
            if not reminder.is_enabled:
                continue
            days = (
                set(_WEEKDAY_CODES)
                if reminder.days_of_week == "daily"
                else {d.strip() for d in reminder.days_of_week.split(",")}
            )
            if today_code not in days:
                continue
            body = f"Take your medication at {reminder.reminder_time.strftime('%H:%M')}."
            if reminder.notes:
                body += f" {reminder.notes}"
            entries.append(
                NotificationRead(
                    id=uuid.uuid5(_COMPUTED_NAMESPACE, f"medication_reminder:{reminder.id}"),
                    type="medication_reminder",
                    title="Medication reminder",
                    body=body,
                    is_read=False,
                    related_resource_id=str(reminder.medication_id),
                    created_at=now_aware,
                    persisted=False,
                )
            )
        return entries


def _from_persisted(notification: Notification) -> NotificationRead:
    return NotificationRead(
        id=notification.id,
        type=notification.type,  # type: ignore[arg-type]  # validated at write time (notify())
        title=notification.title,
        body=notification.body,
        is_read=notification.is_read,
        related_resource_id=notification.related_resource_id,
        created_at=notification.created_at,
        persisted=True,
    )
