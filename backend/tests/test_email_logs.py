import pytest

from app.email.interface import EmailMessage, EmailSender, EmailSendResult
from app.services import health_report_service
from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class _CapturingEmailSender(EmailSender):
    async def send(self, message: EmailMessage) -> EmailSendResult:
        return EmailSendResult(success=True, provider_message_id="test-message-id")


async def test_email_logs_requires_authentication(client):
    resp = await client.get("/api/v1/email-logs")
    assert resp.status_code in (401, 403)


async def test_email_logs_empty_by_default(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.get("/api/v1/email-logs", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_users_cannot_see_each_others_email_logs(client, unique_email, monkeypatch):
    monkeypatch.setattr(
        health_report_service, "get_email_sender", lambda: _CapturingEmailSender()
    )
    data_a = await register_and_login(client, unique_email)
    headers_a = _auth_headers(data_a["access_token"])
    await client.put(
        "/api/v1/profile", headers=headers_a, json={"first_name": "A", "last_name": "Patient"}
    )
    doctor_resp = await client.post(
        "/api/v1/doctors", headers=headers_a, json={"name": "Dr. A", "email": "dra@example.com"}
    )
    doctor_id = doctor_resp.json()["id"]
    share_resp = await client.post(
        "/api/v1/reports/share", headers=headers_a, json={"doctor_contact_id": doctor_id}
    )
    assert share_resp.status_code == 200, share_resp.text

    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_b = _auth_headers(user_b["access_token"])

    resp_a = await client.get("/api/v1/email-logs", headers=headers_a)
    assert len(resp_a.json()) == 1

    resp_b = await client.get("/api/v1/email-logs", headers=headers_b)
    assert resp_b.json() == []
