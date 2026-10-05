import uuid
from datetime import date, timedelta

import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_notifications_requires_authentication(client):
    resp = await client.get("/api/v1/notifications")
    assert resp.status_code in (401, 403)


async def test_ai_summary_generation_creates_persisted_notification(
    client, unique_email, monkeypatch
):
    from app.ai.interface import AIProvider, AISummaryRequest, AISummaryResult
    from app.ai.prompt import REQUIRED_SUMMARY_PREFIX
    from app.services import ai_summary_service

    structured = {
        "summary": REQUIRED_SUMMARY_PREFIX + " Patient reports feeling well.",
        "verified_conditions": [],
        "verified_medications": [],
        "verified_allergies": [],
        "recent_events": [],
        "patient_concerns": None,
        "ai_extracted_notes": [],
        "unavailable": [],
    }

    class _StubProvider(AIProvider):
        async def is_available(self) -> bool:
            return True

        async def generate_summary(self, request: AISummaryRequest) -> AISummaryResult:
            return AISummaryResult(
                summary_text=structured["summary"],
                structured_summary=structured,
                model_name="stub-model",
            )

    monkeypatch.setattr(ai_summary_service, "get_ai_provider", lambda: _StubProvider())

    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    await client.post(
        "/api/v1/conditions", headers=headers, json={"name": "Asthma"}
    )
    await client.post("/api/v1/health-snapshots/generate", headers=headers)
    await client.post("/api/v1/ai-summaries/generate", headers=headers, json={})

    list_resp = await client.get("/api/v1/notifications", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    notifications = list_resp.json()
    ai_ready = [n for n in notifications if n["type"] == "ai_summary_ready"]
    assert len(ai_ready) == 1
    assert ai_ready[0]["is_read"] is False
    assert ai_ready[0]["persisted"] is True


async def test_mark_notification_read(client, unique_email, monkeypatch):
    from app.ai.interface import AIProvider, AISummaryRequest, AISummaryResult
    from app.ai.prompt import REQUIRED_SUMMARY_PREFIX
    from app.services import ai_summary_service

    structured = {
        "summary": REQUIRED_SUMMARY_PREFIX + " Patient reports feeling well.",
        "verified_conditions": [],
        "verified_medications": [],
        "verified_allergies": [],
        "recent_events": [],
        "patient_concerns": None,
        "ai_extracted_notes": [],
        "unavailable": [],
    }

    class _StubProvider(AIProvider):
        async def is_available(self) -> bool:
            return True

        async def generate_summary(self, request: AISummaryRequest) -> AISummaryResult:
            return AISummaryResult(
                summary_text=structured["summary"],
                structured_summary=structured,
                model_name="stub-model",
            )

    monkeypatch.setattr(ai_summary_service, "get_ai_provider", lambda: _StubProvider())

    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    await client.post("/api/v1/conditions", headers=headers, json={"name": "Asthma"})
    await client.post("/api/v1/health-snapshots/generate", headers=headers)
    await client.post("/api/v1/ai-summaries/generate", headers=headers, json={})

    notifications = (await client.get("/api/v1/notifications", headers=headers)).json()
    notification_id = next(n["id"] for n in notifications if n["type"] == "ai_summary_ready")

    read_resp = await client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=headers
    )
    assert read_resp.status_code == 200, read_resp.text
    assert read_resp.json()["is_read"] is True

    unread_only = (
        await client.get("/api/v1/notifications?unread_only=true", headers=headers)
    ).json()
    assert notification_id not in [n["id"] for n in unread_only if n["persisted"]]


async def test_mark_nonexistent_notification_read_returns_404(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.patch(
        f"/api/v1/notifications/{uuid.uuid4()}/read", headers=headers
    )
    assert resp.status_code == 404


async def test_users_cannot_mark_each_others_notifications_read(client, unique_email, monkeypatch):
    from app.ai.interface import AIProvider, AISummaryRequest, AISummaryResult
    from app.ai.prompt import REQUIRED_SUMMARY_PREFIX
    from app.services import ai_summary_service

    structured = {
        "summary": REQUIRED_SUMMARY_PREFIX + " Patient reports feeling well.",
        "verified_conditions": [],
        "verified_medications": [],
        "verified_allergies": [],
        "recent_events": [],
        "patient_concerns": None,
        "ai_extracted_notes": [],
        "unavailable": [],
    }

    class _StubProvider(AIProvider):
        async def is_available(self) -> bool:
            return True

        async def generate_summary(self, request: AISummaryRequest) -> AISummaryResult:
            return AISummaryResult(
                summary_text=structured["summary"],
                structured_summary=structured,
                model_name="stub-model",
            )

    monkeypatch.setattr(ai_summary_service, "get_ai_provider", lambda: _StubProvider())

    user_a = await register_and_login(client, unique_email)
    headers_a = _auth_headers(user_a["access_token"])
    await client.post("/api/v1/conditions", headers=headers_a, json={"name": "Asthma"})
    await client.post("/api/v1/health-snapshots/generate", headers=headers_a)
    await client.post("/api/v1/ai-summaries/generate", headers=headers_a, json={})
    notifications_a = (await client.get("/api/v1/notifications", headers=headers_a)).json()
    notification_id = next(n["id"] for n in notifications_a if n["type"] == "ai_summary_ready")

    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_b = _auth_headers(user_b["access_token"])

    resp = await client.patch(
        f"/api/v1/notifications/{notification_id}/read", headers=headers_b
    )
    assert resp.status_code == 404

    # User B's own notification list is empty -- IDOR safe.
    assert (await client.get("/api/v1/notifications", headers=headers_b)).json() == []


async def test_computed_appointment_approaching_notification(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    # Use tomorrow to stay safely within the 48h window regardless of
    # current time-of-day.
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    create_resp = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={"appointment_date": tomorrow, "reason": "Checkup"},
    )
    assert create_resp.status_code == 201, create_resp.text

    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    computed = [n for n in resp.json() if n["type"] == "appointment_approaching"]
    assert len(computed) == 1
    assert computed[0]["persisted"] is False

    # A computed notification's id never matches a stored row.
    patch_resp = await client.patch(
        f"/api/v1/notifications/{computed[0]['id']}/read", headers=headers
    )
    assert patch_resp.status_code == 404


async def test_computed_medication_reminder_notification(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    med_resp = await client.post(
        "/api/v1/medications", headers=headers, json={"name": "Metformin"}
    )
    medication_id = med_resp.json()["id"]
    await client.post(
        f"/api/v1/medications/{medication_id}/reminders",
        headers=headers,
        json={"reminder_time": "08:00:00", "days_of_week": "daily"},
    )

    resp = await client.get("/api/v1/notifications", headers=headers)
    assert resp.status_code == 200
    computed = [n for n in resp.json() if n["type"] == "medication_reminder"]
    assert len(computed) == 1
    assert computed[0]["persisted"] is False
