from fastapi import APIRouter

from app.api.v1 import (
    account,
    ai_summaries,
    allergies,
    appointments,
    audit_logs,
    auth,
    conditions,
    contact,
    dashboard,
    doctors,
    documents,
    email_logs,
    family,
    health,
    health_snapshots,
    journal,
    medications,
    notifications,
    preferences,
    profile,
    reports,
    shared_reports,
    timeline,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(account.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(dashboard.router)
api_router.include_router(documents.router)
api_router.include_router(medications.router)
api_router.include_router(allergies.router)
api_router.include_router(conditions.router)
api_router.include_router(doctors.router)
api_router.include_router(appointments.router)
api_router.include_router(timeline.router)
api_router.include_router(journal.router)
api_router.include_router(health_snapshots.router)
api_router.include_router(ai_summaries.router)
api_router.include_router(reports.router)
api_router.include_router(shared_reports.router)
api_router.include_router(contact.router)
api_router.include_router(email_logs.router)
api_router.include_router(family.router)
api_router.include_router(preferences.router)
api_router.include_router(notifications.router)
api_router.include_router(audit_logs.router)
