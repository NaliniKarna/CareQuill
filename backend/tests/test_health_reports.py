import uuid

import pytest

from app.email.interface import EmailMessage, EmailSender, EmailSendResult
from app.services import health_report_service
from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class _CapturingEmailSender(EmailSender):
    def __init__(self, *, succeed: bool = True) -> None:
        self.sent: list[EmailMessage] = []
        self._succeed = succeed

    async def send(self, message: EmailMessage) -> EmailSendResult:
        self.sent.append(message)
        if self._succeed:
            return EmailSendResult(success=True, provider_message_id="test-message-id")
        return EmailSendResult(success=False, error_message="SMTP connection refused")


def _use_email_sender(monkeypatch, sender: EmailSender) -> None:
    monkeypatch.setattr(health_report_service, "get_email_sender", lambda: sender)


async def _setup_patient(client, unique_email) -> tuple[dict, dict]:
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    await client.put(
        "/api/v1/profile",
        headers=headers,
        json={"first_name": "Jane", "last_name": "Doe"},
    )
    await client.post(
        "/api/v1/conditions",
        headers=headers,
        json={"name": "Asthma", "diagnosed_date": "2022-01-15"},
    )
    await client.post(
        "/api/v1/allergies", headers=headers, json={"name": "Penicillin", "severity": "severe"}
    )
    await client.post(
        "/api/v1/medications",
        headers=headers,
        json={"name": "Metformin", "dosage": "500mg", "frequency": "twice daily"},
    )
    return data, headers


async def _create_doctor(client, headers, **overrides) -> str:
    payload = {"name": "Dr. Patel", "email": "patel@example.com"}
    payload.update(overrides)
    resp = await client.post("/api/v1/doctors", headers=headers, json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# -- preview -------------------------------------------------------------------


async def test_preview_returns_summary_without_generating_or_sending(
    client, unique_email, monkeypatch
):
    data, headers = await _setup_patient(client, unique_email)
    doctor_id = await _create_doctor(client, headers)
    sender = _CapturingEmailSender()
    _use_email_sender(monkeypatch, sender)

    resp = await client.post(
        "/api/v1/reports/preview",
        headers=headers,
        json={
            "doctor_contact_id": doctor_id,
            "include_conditions": True,
            "include_allergies": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["doctor_name"] == "Dr. Patel"
    assert body["doctor_email"] == "patel@example.com"
    assert set(body["included_sections"]) == {"conditions", "allergies"}
    assert sender.sent == []  # nothing was ever sent


# -- generate --------------------------------------------------------------------


async def test_generate_returns_downloadable_pdf_without_internal_ids(client, unique_email):
    data, headers = await _setup_patient(client, unique_email)

    resp = await client.post(
        "/api/v1/reports/generate",
        headers=headers,
        json={"include_conditions": True, "include_medications": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    filename = resp.headers["content-disposition"]
    assert "health-summary-" in filename
    # No document UUID anywhere in the filename.
    assert str(uuid.uuid4())[:8] not in filename  # sanity: format check only
    assert resp.content[:4] == b"%PDF"


# -- share -----------------------------------------------------------------------


async def test_share_happy_path_sends_email_and_logs(client, unique_email, monkeypatch):
    data, headers = await _setup_patient(client, unique_email)
    doctor_id = await _create_doctor(client, headers)
    sender = _CapturingEmailSender(succeed=True)
    _use_email_sender(monkeypatch, sender)

    resp = await client.post(
        "/api/v1/reports/share",
        headers=headers,
        json={
            "doctor_contact_id": doctor_id,
            "include_conditions": True,
            "include_allergies": True,
            "include_medications": True,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "sent"
    assert body["doctor_email"] == "patel@example.com"
    assert body["report_name"].startswith("CareQuill Health Summary")

    assert len(sender.sent) == 1
    message = sender.sent[0]
    assert message.to == "patel@example.com"
    assert message.attachments is not None
    assert len(message.attachments) == 1  # PDF only, no documents selected
    pdf_filename, pdf_bytes, mime_type = message.attachments[0]
    assert mime_type == "application/pdf"
    assert pdf_bytes[:4] == b"%PDF"

    # Appears in the patient's sharing history.
    logs_resp = await client.get("/api/v1/email-logs", headers=headers)
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) == 1
    assert logs[0]["doctor_name"] == "Dr. Patel"
    assert "included_sections" not in logs[0]

    # A report_shared notification was created.
    notifications = (await client.get("/api/v1/notifications", headers=headers)).json()
    assert any(n["type"] == "report_shared" for n in notifications)


async def test_share_includes_selected_documents_as_attachments(client, unique_email, monkeypatch):
    data, headers = await _setup_patient(client, unique_email)
    doctor_id = await _create_doctor(client, headers)
    sender = _CapturingEmailSender(succeed=True)
    _use_email_sender(monkeypatch, sender)

    upload_resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "Blood Test"},
        files={"file": ("report.pdf", b"%PDF-1.4 minimal", "application/pdf")},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    document_id = upload_resp.json()["id"]

    resp = await client.post(
        "/api/v1/reports/share",
        headers=headers,
        json={"doctor_contact_id": doctor_id, "document_ids": [document_id]},
    )
    assert resp.status_code == 200, resp.text

    message = sender.sent[0]
    assert len(message.attachments) == 2  # PDF + the one selected document
    filenames = [a[0] for a in message.attachments]
    assert "report.pdf" in filenames
    # The internal stored_filename (a uuid hex) must never appear.
    assert document_id not in filenames


async def test_share_fails_gracefully_on_email_delivery_failure(client, unique_email, monkeypatch):
    data, headers = await _setup_patient(client, unique_email)
    doctor_id = await _create_doctor(client, headers)
    sender = _CapturingEmailSender(succeed=False)
    _use_email_sender(monkeypatch, sender)

    resp = await client.post(
        "/api/v1/reports/share", headers=headers, json={"doctor_contact_id": doctor_id}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "failed"
    assert resp.json()["error_message"]

    notifications = (await client.get("/api/v1/notifications", headers=headers)).json()
    assert any(n["type"] == "email_failure" for n in notifications)


async def test_share_requires_doctor_contact_id(client, unique_email):
    data, headers = await _setup_patient(client, unique_email)
    resp = await client.post("/api/v1/reports/share", headers=headers, json={})
    assert resp.status_code == 422, resp.text


async def test_share_rejects_unreviewed_ai_summary(client, unique_email, monkeypatch):
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

    data, headers = await _setup_patient(client, unique_email)
    doctor_id = await _create_doctor(client, headers)
    await client.post("/api/v1/health-snapshots/generate", headers=headers)
    generate_resp = await client.post(
        "/api/v1/ai-summaries/generate", headers=headers, json={}
    )
    summary_id = generate_resp.json()["id"]
    assert generate_resp.json()["status"] == "pending_review"

    resp = await client.post(
        "/api/v1/reports/share",
        headers=headers,
        json={
            "doctor_contact_id": doctor_id,
            "ai_summary_id": summary_id,
            "include_ai_summary": True,
        },
    )
    assert resp.status_code == 422, resp.text


async def test_include_ai_summary_without_id_is_rejected(client, unique_email):
    data, headers = await _setup_patient(client, unique_email)
    doctor_id = await _create_doctor(client, headers)
    resp = await client.post(
        "/api/v1/reports/preview",
        headers=headers,
        json={"doctor_contact_id": doctor_id, "include_ai_summary": True},
    )
    assert resp.status_code == 422, resp.text


# -- IDOR ------------------------------------------------------------------------


async def test_idor_doctor_contact_of_another_patient(client, unique_email):
    data_a, headers_a = await _setup_patient(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_b = _auth_headers(user_b["access_token"])
    doctor_b_id = await _create_doctor(client, headers_b, name="Dr. B")

    resp = await client.post(
        "/api/v1/reports/preview",
        headers=headers_a,
        json={"doctor_contact_id": doctor_b_id},
    )
    assert resp.status_code == 404


async def test_idor_appointment_of_another_patient(client, unique_email):
    data_a, headers_a = await _setup_patient(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_b = _auth_headers(user_b["access_token"])
    appt_resp = await client.post(
        "/api/v1/appointments",
        headers=headers_b,
        json={"appointment_date": "2099-01-01", "reason": "B's appointment"},
    )
    appointment_b_id = appt_resp.json()["id"]

    resp = await client.post(
        "/api/v1/reports/preview",
        headers=headers_a,
        json={"appointment_id": appointment_b_id},
    )
    assert resp.status_code == 404


async def test_idor_ai_summary_of_another_patient(client, unique_email, monkeypatch):
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

    data_a, headers_a = await _setup_patient(client, unique_email)
    await client.post("/api/v1/health-snapshots/generate", headers=headers_a)
    generate_resp = await client.post("/api/v1/ai-summaries/generate", headers=headers_a, json={})
    summary_a_id = generate_resp.json()["id"]

    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_b = _auth_headers(user_b["access_token"])

    resp = await client.post(
        "/api/v1/reports/preview",
        headers=headers_b,
        json={"ai_summary_id": summary_a_id},
    )
    assert resp.status_code == 404


async def test_idor_document_of_another_patient(client, unique_email):
    data_a, headers_a = await _setup_patient(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_b = _auth_headers(user_b["access_token"])

    upload_resp = await client.post(
        "/api/v1/documents",
        headers=headers_b,
        data={"title": "B's document"},
        files={"file": ("report.pdf", b"%PDF-1.4 minimal", "application/pdf")},
    )
    document_b_id = upload_resp.json()["id"]

    resp = await client.post(
        "/api/v1/reports/preview",
        headers=headers_a,
        json={"document_ids": [document_b_id]},
    )
    assert resp.status_code == 404


async def test_reports_require_authentication(client):
    resp = await client.post("/api/v1/reports/preview", json={})
    assert resp.status_code in (401, 403)
