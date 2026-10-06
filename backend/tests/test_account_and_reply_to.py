"""Patient data control (export / delete) and Reply-To on shared emails."""
import io
import json
import zipfile

import pytest
from sqlalchemy import func, select

from app.email.interface import EmailMessage, EmailSender, EmailSendResult
from app.models.audit_log import AuditLog
from app.models.medical_document import MedicalDocument
from app.models.medication import Medication
from app.models.user import User
from app.services import health_report_service
from app.storage.factory import get_storage_backend
from tests.conftest import TestSessionLocal, register_and_login
from tests.test_documents import _build_test_pdf_bytes as _pdf

pytestmark = pytest.mark.asyncio


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class _Capture(EmailSender):
    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> EmailSendResult:
        self.sent.append(message)
        return EmailSendResult(success=True)


# --------------------------------------------------------------------------
# Reply-To
# --------------------------------------------------------------------------
async def test_report_share_sets_reply_to_to_the_patient(client, unique_email, monkeypatch):
    data = await register_and_login(client, unique_email)
    headers = _h(data["access_token"])
    await client.put(
        "/api/v1/profile", headers=headers, json={"first_name": "Jane", "last_name": "Doe"}
    )
    doctor = await client.post(
        "/api/v1/doctors", headers=headers, json={"name": "Dr P", "email": "p@example.com"}
    )
    sender = _Capture()
    monkeypatch.setattr(health_report_service, "get_email_sender", lambda: sender)

    resp = await client.post(
        "/api/v1/reports/share",
        headers=headers,
        json={"doctor_contact_id": doctor.json()["id"]},
    )
    assert resp.status_code == 200, resp.text
    assert sender.sent[0].reply_to == unique_email.lower()


async def test_smtp_sets_reply_to_header(monkeypatch):
    from app.email import smtp_email

    captured = {}

    class _FakeSMTP:
        def __init__(self, *a, **k) -> None: ...
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def starttls(self): ...
        def login(self, *a): ...
        def send_message(self, msg):
            captured["reply_to"] = msg["Reply-To"]

    monkeypatch.setattr(smtp_email.smtplib, "SMTP", _FakeSMTP)
    result = await smtp_email.SMTPEmailSender().send(
        EmailMessage(
            to="d@example.com", subject="s", html_body="<p>x</p>", reply_to="pt@example.com"
        )
    )
    assert result.success and captured["reply_to"] == "pt@example.com"


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------
async def _seed(client, email) -> dict:
    data = await register_and_login(client, email)
    headers = _h(data["access_token"])
    await client.post(
        "/api/v1/medications", headers=headers, json={"name": "Metformin", "dosage": "500mg"}
    )
    up = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("report.pdf", _pdf("Hemoglobin 13 g/dL"), "application/pdf")},
        data={"title": "Lab", "category": "lab_report"},
    )
    assert up.status_code == 201, up.text
    return {"headers": headers, "doc_id": up.json()["id"], "data": data}


async def test_export_contains_own_data_and_original_file_but_no_secrets(client, unique_email):
    seeded = await _seed(client, unique_email)
    resp = await client.get("/api/v1/account/export", headers=seeded["headers"])
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "no-store" in resp.headers["cache-control"]

    archive = zipfile.ZipFile(io.BytesIO(resp.content))
    names = archive.namelist()
    exported = json.loads(archive.read("data.json"))
    assert exported["account"]["email"] == unique_email.lower()
    assert [m["name"] for m in exported["medications"]] == ["Metformin"]
    assert exported["documents"][0]["file_included"] is True
    assert any(n.startswith("documents/") and n.endswith("report.pdf") for n in names)
    raw = archive.read("data.json").decode()
    for secret in ("password_hash", "storage_path", "stored_filename", "token_hash"):
        assert secret not in raw


async def test_export_never_includes_another_patients_data(client, unique_email):
    await _seed(client, unique_email)
    other = await register_and_login(client, "someone-else-" + unique_email)
    resp = await client.get("/api/v1/account/export", headers=_h(other["access_token"]))
    exported = json.loads(zipfile.ZipFile(io.BytesIO(resp.content)).read("data.json"))
    assert exported["medications"] == []
    assert exported["documents"] == []
    assert exported["account"]["email"] != unique_email.lower()


async def test_export_requires_authentication(client):
    assert (await client.get("/api/v1/account/export")).status_code in (401, 403)


# --------------------------------------------------------------------------
# Delete
# --------------------------------------------------------------------------
async def test_delete_requires_correct_password_and_confirmation(client, unique_email):
    seeded = await _seed(client, unique_email)
    headers = seeded["headers"]
    wrong_pw = await client.post(
        "/api/v1/account/delete",
        headers=headers,
        json={"password": "not-the-password", "confirmation": "DELETE"},
    )
    assert wrong_pw.status_code == 401
    no_phrase = await client.post(
        "/api/v1/account/delete",
        headers=headers,
        json={"password": "SuperSecret123", "confirmation": "yes"},
    )
    assert no_phrase.status_code in (400, 422)
    # Nothing was removed.
    meds = await client.get("/api/v1/medications", headers=headers)
    assert meds.status_code == 200


async def test_delete_removes_everything_including_files_and_blocks_login(client, unique_email):
    seeded = await _seed(client, unique_email)
    headers = seeded["headers"]
    async with TestSessionLocal() as s:
        storage_path = (await s.execute(select(MedicalDocument.storage_path))).scalar_one()
    storage = get_storage_backend()
    assert await storage.exists(storage_path=storage_path)

    resp = await client.post(
        "/api/v1/account/delete",
        headers=headers,
        json={"password": "SuperSecret123", "confirmation": "DELETE"},
    )
    assert resp.status_code == 204, resp.text

    async with TestSessionLocal() as s:
        assert (await s.execute(select(func.count()).select_from(User))).scalar_one() == 0
        assert (await s.execute(select(func.count()).select_from(Medication))).scalar_one() == 0
        docs = select(func.count()).select_from(MedicalDocument)
        assert (await s.execute(docs)).scalar_one() == 0
        # Audit rows survive but are anonymised.
        linked = select(func.count()).select_from(AuditLog).where(AuditLog.user_id.is_not(None))
        orphaned = (await s.execute(linked)).scalar_one()
        assert orphaned == 0
    assert not await storage.exists(storage_path=storage_path)

    # The old token and the old credentials are now useless.
    assert (await client.get("/api/v1/medications", headers=headers)).status_code == 401
    login = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "SuperSecret123"}
    )
    assert login.status_code == 401


async def test_delete_only_affects_the_caller(client, unique_email):
    await _seed(client, unique_email)
    other = await _seed(client, "other-" + unique_email)
    victim = await register_and_login(client, "victim-" + unique_email)
    resp = await client.post(
        "/api/v1/account/delete",
        headers=_h(victim["access_token"]),
        json={"password": "SuperSecret123", "confirmation": "DELETE"},
    )
    assert resp.status_code == 204
    docs = await client.get("/api/v1/documents", headers=other["headers"])
    assert docs.json()["total"] == 1
    async with TestSessionLocal() as s:
        assert (await s.execute(select(func.count()).select_from(User))).scalar_one() == 2
