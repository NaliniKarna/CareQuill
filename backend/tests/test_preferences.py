import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_preferences_requires_authentication(client):
    resp = await client.get("/api/v1/preferences")
    assert resp.status_code in (401, 403)


async def test_get_preferences_returns_defaults_on_first_read(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    resp = await client.get("/api/v1/preferences", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data_sharing_consent"] is True
    assert body["notification_prefs"] == {
        "appointment_reminders": True,
        "medication_reminders": True,
        "ai_summary_ready": True,
        "document_processed": True,
        "report_shared": True,
        "email_failures": True,
    }


async def test_update_preferences_partial_update(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    resp = await client.put(
        "/api/v1/preferences",
        headers=headers,
        json={"data_sharing_consent": False},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["data_sharing_consent"] is False
    # Notification prefs were untouched by the partial update.
    assert body["notification_prefs"]["appointment_reminders"] is True

    resp2 = await client.put(
        "/api/v1/preferences",
        headers=headers,
        json={"notification_prefs": {"appointment_reminders": False}},
    )
    assert resp2.status_code == 200, resp2.text
    body2 = resp2.json()
    assert body2["notification_prefs"]["appointment_reminders"] is False
    # data_sharing_consent from the previous update is preserved.
    assert body2["data_sharing_consent"] is False


async def test_users_have_independent_preferences(client, unique_email):
    user_a = await register_and_login(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    await client.put(
        "/api/v1/preferences", headers=headers_a, json={"data_sharing_consent": False}
    )

    resp_b = await client.get("/api/v1/preferences", headers=headers_b)
    assert resp_b.json()["data_sharing_consent"] is True

    resp_a = await client.get("/api/v1/preferences", headers=headers_a)
    assert resp_a.json()["data_sharing_consent"] is False


async def test_data_sharing_consent_off_skips_ocr(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    await client.put(
        "/api/v1/preferences", headers=headers, json={"data_sharing_consent": False}
    )

    upload_resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "Blood test"},
        files={"file": ("report.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    document_id = upload_resp.json()["id"]

    # The background OCR task has already run by the time the ASGI
    # request/response cycle completes (see test_documents.py).
    get_resp = await client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["ocr_status"] == "skipped"
