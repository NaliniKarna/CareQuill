import uuid

import pytest

from app.ai.interface import AIProvider, AISummaryRequest, AISummaryResult
from app.ai.prompt import REQUIRED_SUMMARY_PREFIX
from app.email.interface import EmailMessage, EmailSender, EmailSendResult
from app.models.ai_summary import AISummary
from app.services import ai_summary_service
from tests.conftest import TestSessionLocal, register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _good_structured(**overrides) -> dict:
    base = {
        "summary": REQUIRED_SUMMARY_PREFIX + " Patient reports feeling generally well.",
        "verified_conditions": ["Asthma"],
        "verified_medications": ["Metformin 500mg twice daily"],
        "verified_allergies": [],
        "recent_events": [],
        "patient_concerns": None,
        "ai_extracted_notes": [],
        "unavailable": [],
    }
    base.update(overrides)
    return base


def _good_result(**overrides) -> AISummaryResult:
    structured = _good_structured(**overrides)
    return AISummaryResult(
        summary_text=structured["summary"],
        structured_summary=structured,
        model_name="stub-model",
    )


def _bad_result() -> AISummaryResult:
    return AISummaryResult(
        summary_text="this is not valid json at all {{{",
        structured_summary=None,
        model_name="stub-model",
    )


class _StubAIProvider(AIProvider):
    """Controllable fake AIProvider -- returns queued responses in order and
    records every request it was called with."""

    def __init__(self, responses: list[AISummaryResult], *, available: bool = True) -> None:
        self._responses = list(responses)
        self._available = available
        self.calls: list[AISummaryRequest] = []

    async def is_available(self) -> bool:
        return self._available

    async def generate_summary(self, request: AISummaryRequest) -> AISummaryResult:
        self.calls.append(request)
        if not self._responses:
            raise RuntimeError("stub provider ran out of queued responses")
        return self._responses.pop(0)


class _CapturingEmailSender(EmailSender):
    def __init__(self, *, succeed: bool = True) -> None:
        self.sent: list[EmailMessage] = []
        self._succeed = succeed

    async def send(self, message: EmailMessage) -> EmailSendResult:
        self.sent.append(message)
        if self._succeed:
            return EmailSendResult(success=True, provider_message_id="test-message-id")
        return EmailSendResult(success=False, error_message="SMTP connection refused")


def _use_provider(monkeypatch, provider: AIProvider) -> None:
    monkeypatch.setattr(ai_summary_service, "get_ai_provider", lambda: provider)


def _use_email_sender(monkeypatch, sender: EmailSender) -> None:
    monkeypatch.setattr(ai_summary_service, "get_email_sender", lambda: sender)


async def _setup_patient_with_snapshot(client, unique_email) -> tuple[dict, dict]:
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    await client.post(
        "/api/v1/conditions",
        headers=headers,
        json={"name": "Asthma", "diagnosed_date": "2022-01-15"},
    )
    await client.post(
        "/api/v1/medications",
        headers=headers,
        json={"name": "Metformin", "dosage": "500mg", "frequency": "twice daily"},
    )
    return data, headers


# -- generation --------------------------------------------------------------


async def test_generate_requires_a_snapshot_first(client, unique_email, monkeypatch):
    _use_provider(monkeypatch, _StubAIProvider([_good_result()]))
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    resp = await client.post("/api/v1/ai-summaries/generate", headers=headers, json={})
    assert resp.status_code == 422, resp.text


async def test_generate_succeeds_and_returns_pending_review_summary(
    client, unique_email, monkeypatch
):
    provider = _StubAIProvider([_good_result()])
    _use_provider(monkeypatch, provider)
    data, headers = await _setup_patient_with_snapshot(client, unique_email)
    await client.post("/api/v1/health-snapshots/generate", headers=headers)

    resp = await client.post(
        "/api/v1/ai-summaries/generate",
        headers=headers,
        json={"patient_concerns": "Occasional headaches"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending_review"
    assert body["summary_text"].startswith(REQUIRED_SUMMARY_PREFIX)
    assert body["edited_summary_text"] is None
    assert body["model_name"] == "stub-model"
    assert body["health_snapshot_id"] is not None

    # The prompt actually carried the verified snapshot data + patient concerns.
    sent_request = provider.calls[0]
    assert sent_request.patient_concerns == "Occasional headaches"
    assert sent_request.snapshot_data["conditions"][0]["name"] == "Asthma"


async def test_generate_disabled_when_ai_provider_unavailable(client, unique_email, monkeypatch):
    _use_provider(monkeypatch, _StubAIProvider([_good_result()], available=False))
    data, headers = await _setup_patient_with_snapshot(client, unique_email)
    await client.post("/api/v1/health-snapshots/generate", headers=headers)

    resp = await client.post("/api/v1/ai-summaries/generate", headers=headers, json={})
    assert resp.status_code == 422, resp.text


async def test_generate_retries_once_on_malformed_json_then_succeeds(
    client, unique_email, monkeypatch
):
    provider = _StubAIProvider([_bad_result(), _good_result()])
    _use_provider(monkeypatch, provider)
    data, headers = await _setup_patient_with_snapshot(client, unique_email)
    await client.post("/api/v1/health-snapshots/generate", headers=headers)

    resp = await client.post("/api/v1/ai-summaries/generate", headers=headers, json={})
    assert resp.status_code == 201, resp.text
    assert resp.json()["summary_text"].startswith(REQUIRED_SUMMARY_PREFIX)
    assert len(provider.calls) == 2
    # The retry must ask more strictly for valid JSON only.
    assert provider.calls[1].strict_json_retry is True


async def test_generate_fails_after_malformed_json_twice(client, unique_email, monkeypatch):
    provider = _StubAIProvider([_bad_result(), _bad_result()])
    _use_provider(monkeypatch, provider)
    data, headers = await _setup_patient_with_snapshot(client, unique_email)
    await client.post("/api/v1/health-snapshots/generate", headers=headers)

    resp = await client.post("/api/v1/ai-summaries/generate", headers=headers, json={})
    assert resp.status_code == 502, resp.text
    assert resp.json()["error"]["code"] == "ai_generation_failed"
    assert len(provider.calls) == 2

    # Nothing malformed was ever persisted.
    async with TestSessionLocal() as session:
        from sqlalchemy import select

        result = await session.execute(select(AISummary))
        assert result.scalars().all() == []


# -- edit -> confirm -> share workflow ---------------------------------------


async def test_edit_confirm_share_happy_path_uses_edited_text(client, unique_email, monkeypatch):
    provider = _StubAIProvider([_good_result()])
    email_sender = _CapturingEmailSender(succeed=True)
    _use_provider(monkeypatch, provider)
    _use_email_sender(monkeypatch, email_sender)

    data, headers = await _setup_patient_with_snapshot(client, unique_email)
    await client.post("/api/v1/health-snapshots/generate", headers=headers)

    generate_resp = await client.post("/api/v1/ai-summaries/generate", headers=headers, json={})
    summary_id = generate_resp.json()["id"]

    edited_text = REQUIRED_SUMMARY_PREFIX + " Patient edited this summary by hand."
    edit_resp = await client.patch(
        f"/api/v1/ai-summaries/{summary_id}",
        headers=headers,
        json={"edited_summary_text": edited_text},
    )
    assert edit_resp.status_code == 200, edit_resp.text
    assert edit_resp.json()["edited_summary_text"] == edited_text

    confirm_resp = await client.post(f"/api/v1/ai-summaries/{summary_id}/confirm", headers=headers)
    assert confirm_resp.status_code == 200, confirm_resp.text
    assert confirm_resp.json()["status"] == "reviewed"
    assert confirm_resp.json()["reviewed_at"] is not None

    doctor_resp = await client.post(
        "/api/v1/doctors",
        headers=headers,
        json={"name": "Dr. Shrestha", "email": "shrestha@example.com"},
    )
    doctor_id = doctor_resp.json()["id"]

    share_resp = await client.post(
        f"/api/v1/ai-summaries/{summary_id}/share",
        headers=headers,
        json={"doctor_contact_id": doctor_id},
    )
    assert share_resp.status_code == 200, share_resp.text
    assert share_resp.json()["status"] == "sent"
    assert share_resp.json()["doctor_email"] == "shrestha@example.com"

    final_status_resp = await client.get(f"/api/v1/ai-summaries/{summary_id}", headers=headers)
    assert final_status_resp.json()["status"] == "shared"

    assert len(email_sender.sent) == 1
    sent_message = email_sender.sent[0]
    assert sent_message.to == "shrestha@example.com"
    assert edited_text in sent_message.text_body
    # The original, unedited draft must never be sent once the patient edited it.
    assert edited_text != generate_resp.json()["summary_text"]
    assert generate_resp.json()["summary_text"] not in sent_message.text_body


async def test_share_fails_gracefully_when_email_delivery_fails(client, unique_email, monkeypatch):
    provider = _StubAIProvider([_good_result()])
    email_sender = _CapturingEmailSender(succeed=False)
    _use_provider(monkeypatch, provider)
    _use_email_sender(monkeypatch, email_sender)

    data, headers = await _setup_patient_with_snapshot(client, unique_email)
    await client.post("/api/v1/health-snapshots/generate", headers=headers)
    generate_resp = await client.post("/api/v1/ai-summaries/generate", headers=headers, json={})
    summary_id = generate_resp.json()["id"]
    await client.post(f"/api/v1/ai-summaries/{summary_id}/confirm", headers=headers)

    doctor_resp = await client.post(
        "/api/v1/doctors", headers=headers, json={"name": "Dr. Lee", "email": "lee@example.com"}
    )
    doctor_id = doctor_resp.json()["id"]

    share_resp = await client.post(
        f"/api/v1/ai-summaries/{summary_id}/share",
        headers=headers,
        json={"doctor_contact_id": doctor_id},
    )
    assert share_resp.status_code == 200, share_resp.text
    assert share_resp.json()["status"] == "failed"
    assert share_resp.json()["error_message"]

    # A failed send must never flip the summary to "shared".
    status_resp = await client.get(f"/api/v1/ai-summaries/{summary_id}", headers=headers)
    assert status_resp.json()["status"] == "reviewed"


async def test_share_rejected_while_still_pending_review(client, unique_email, monkeypatch):
    provider = _StubAIProvider([_good_result()])
    _use_provider(monkeypatch, provider)
    data, headers = await _setup_patient_with_snapshot(client, unique_email)
    await client.post("/api/v1/health-snapshots/generate", headers=headers)
    generate_resp = await client.post("/api/v1/ai-summaries/generate", headers=headers, json={})
    summary_id = generate_resp.json()["id"]

    doctor_resp = await client.post(
        "/api/v1/doctors", headers=headers, json={"name": "Dr. Lee", "email": "lee@example.com"}
    )
    doctor_id = doctor_resp.json()["id"]

    share_resp = await client.post(
        f"/api/v1/ai-summaries/{summary_id}/share",
        headers=headers,
        json={"doctor_contact_id": doctor_id},
    )
    assert share_resp.status_code == 409, share_resp.text


async def test_share_rejected_for_doctor_contact_of_a_different_patient(
    client, unique_email, monkeypatch
):
    """IDOR: sharing must validate the doctor contact belongs to the
    sharing patient, not just that it exists."""
    provider = _StubAIProvider([_good_result()])
    _use_provider(monkeypatch, provider)

    user_a_data, headers_a = await _setup_patient_with_snapshot(client, unique_email)
    await client.post("/api/v1/health-snapshots/generate", headers=headers_a)
    generate_resp = await client.post("/api/v1/ai-summaries/generate", headers=headers_a, json={})
    summary_id = generate_resp.json()["id"]
    await client.post(f"/api/v1/ai-summaries/{summary_id}/confirm", headers=headers_a)

    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_b = _auth_headers(user_b["access_token"])
    doctor_b_resp = await client.post(
        "/api/v1/doctors",
        headers=headers_b,
        json={"name": "Dr. B's Doctor", "email": "b@example.com"},
    )
    doctor_b_id = doctor_b_resp.json()["id"]

    share_resp = await client.post(
        f"/api/v1/ai-summaries/{summary_id}/share",
        headers=headers_a,
        json={"doctor_contact_id": doctor_b_id},
    )
    assert share_resp.status_code == 404, share_resp.text


# -- IDOR ---------------------------------------------------------------------


async def test_ai_summaries_require_authentication(client):
    resp = await client.get("/api/v1/ai-summaries")
    assert resp.status_code in (401, 403)


async def test_users_cannot_access_each_others_ai_summaries(client, unique_email, monkeypatch):
    provider = _StubAIProvider([_good_result()])
    _use_provider(monkeypatch, provider)

    user_a_data, headers_a = await _setup_patient_with_snapshot(client, unique_email)
    await client.post("/api/v1/health-snapshots/generate", headers=headers_a)
    generate_resp = await client.post("/api/v1/ai-summaries/generate", headers=headers_a, json={})
    summary_id = generate_resp.json()["id"]

    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_b = _auth_headers(user_b["access_token"])
    doctor_b_resp = await client.post(
        "/api/v1/doctors", headers=headers_b, json={"name": "Dr. B", "email": "docb@example.com"}
    )
    doctor_b_id = doctor_b_resp.json()["id"]

    assert (
        await client.get(f"/api/v1/ai-summaries/{summary_id}", headers=headers_b)
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/ai-summaries/{summary_id}",
            headers=headers_b,
            json={"edited_summary_text": "hijacked"},
        )
    ).status_code == 404
    assert (
        await client.post(f"/api/v1/ai-summaries/{summary_id}/confirm", headers=headers_b)
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/ai-summaries/{summary_id}/share",
            headers=headers_b,
            json={"doctor_contact_id": doctor_b_id},
        )
    ).status_code == 404
    assert (await client.get("/api/v1/ai-summaries", headers=headers_b)).json() == []

    # User A's own summary is untouched and still reachable by A.
    still_theirs = await client.get(f"/api/v1/ai-summaries/{summary_id}", headers=headers_a)
    assert still_theirs.status_code == 200
    assert still_theirs.json()["patient_id"] == user_a_data["user"]["id"]


async def test_nonexistent_ai_summary_returns_404(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.get(f"/api/v1/ai-summaries/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404
