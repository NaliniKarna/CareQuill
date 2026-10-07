"""QR-code / link sharing of health reports, and the email attachment limit."""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.report_share_link import ReportShareLink
from tests.conftest import register_and_login
from tests.test_health_reports import (
    _CapturingEmailSender,
    _create_doctor,
    _setup_patient,
    _use_email_sender,
)

pytestmark = pytest.mark.asyncio

PDF_BYTES = b"%PDF-1.4 minimal"


async def _upload(client, headers, title="Blood Test") -> str:
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": title},
        files={"file": ("report.pdf", PDF_BYTES, "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_link(client, headers, **report) -> dict:
    body = {"report": {"include_conditions": True, **report}, "expires_in_hours": 24}
    resp = await client.post("/api/v1/reports/share-links", headers=headers, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _token(created: dict) -> str:
    # The token lives in the URL fragment so it never reaches server logs.
    assert "/shared#" in created["url"]
    return created["url"].split("#", 1)[1]


async def test_create_link_returns_fragment_url_and_stores_only_a_hash(client, unique_email):
    _, headers = await _setup_patient(client, unique_email)
    created = await _create_link(client, headers)
    token = _token(created)

    assert created["status"] == "active"
    assert created["url"].startswith(settings.frontend_base_url.rstrip("/"))
    async with AsyncSessionLocal() as session:
        link = (await session.execute(select(ReportShareLink))).scalars().all()[-1]
    assert token not in link.token_hash
    assert len(link.token_hash) == 64

    # The list never shows the URL/token again.
    listed = (await client.get("/api/v1/reports/share-links", headers=headers)).json()
    assert listed[0]["id"] == created["id"]
    assert "url" not in listed[0]


async def test_public_access_serves_report_and_selected_documents_only(client, unique_email):
    _, headers = await _setup_patient(client, unique_email)
    shared_doc = await _upload(client, headers, "Shared scan")
    other_doc = await _upload(client, headers, "Private scan")
    created = await _create_link(client, headers, document_ids=[shared_doc])
    token = _token(created)

    info = await client.post("/api/v1/public/shared-reports/info", json={"token": token})
    assert info.status_code == 200, info.text
    body = info.json()
    assert body["patient_name"] == "Jane Doe"
    assert [d["id"] for d in body["documents"]] == [shared_doc]

    pdf = await client.post("/api/v1/public/shared-reports/report", json={"token": token})
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    doc = await client.post(
        "/api/v1/public/shared-reports/document",
        json={"token": token, "document_id": shared_doc},
    )
    assert doc.status_code == 200
    assert doc.content == PDF_BYTES

    # A document that was not chosen for this link is never served.
    other = await client.post(
        "/api/v1/public/shared-reports/document",
        json={"token": token, "document_id": other_doc},
    )
    assert other.status_code == 404

    listed = (await client.get("/api/v1/reports/share-links", headers=headers)).json()
    assert listed[0]["view_count"] == 1


async def test_invalid_expired_and_revoked_links_all_return_404(client, unique_email):
    _, headers = await _setup_patient(client, unique_email)

    bad = await client.post(
        "/api/v1/public/shared-reports/info", json={"token": "x" * 43}
    )
    assert bad.status_code == 404

    expired = await _create_link(client, headers)
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(ReportShareLink)
            .where(ReportShareLink.id == expired["id"])
            .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )
        await session.commit()
    resp = await client.post(
        "/api/v1/public/shared-reports/report", json={"token": _token(expired)}
    )
    assert resp.status_code == 404

    revoked = await _create_link(client, headers)
    resp = await client.post(
        f"/api/v1/reports/share-links/{revoked['id']}/revoke", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"
    resp = await client.post(
        "/api/v1/public/shared-reports/info", json={"token": _token(revoked)}
    )
    assert resp.status_code == 404
    # Revoking removes the stored PDF snapshot.
    async with AsyncSessionLocal() as session:
        link = await session.get(ReportShareLink, revoked["id"])
        assert link is not None and link.report_storage_path is None


async def test_links_are_owner_only(client, unique_email):
    _, owner_headers = await _setup_patient(client, unique_email)
    created = await _create_link(client, owner_headers)

    other = await register_and_login(client, f"other-{unique_email}")
    other_headers = {"Authorization": f"Bearer {other['access_token']}"}
    resp = await client.post(
        f"/api/v1/reports/share-links/{created['id']}/revoke", headers=other_headers
    )
    assert resp.status_code == 404
    assert (await client.get("/api/v1/reports/share-links", headers=other_headers)).json() == []

    # Another patient's document can't be put into your link.
    other_doc = await _upload(client, other_headers)
    resp = await client.post(
        "/api/v1/reports/share-links",
        headers=owner_headers,
        json={"report": {"document_ids": [other_doc]}, "expires_in_hours": 24},
    )
    assert resp.status_code == 404


async def test_create_link_validates_content_and_expiry(client, unique_email):
    _, headers = await _setup_patient(client, unique_email)
    empty = await client.post(
        "/api/v1/reports/share-links",
        headers=headers,
        json={"report": {}, "expires_in_hours": 24},
    )
    assert empty.status_code == 422 or empty.status_code == 400
    too_long = await client.post(
        "/api/v1/reports/share-links",
        headers=headers,
        json={
            "report": {"include_conditions": True},
            "expires_in_hours": settings.share_link_max_hours + 1,
        },
    )
    assert too_long.status_code in (400, 422)


async def test_email_share_rejects_attachments_over_the_size_limit(
    client, unique_email, monkeypatch
):
    _, headers = await _setup_patient(client, unique_email)
    doctor_id = await _create_doctor(client, headers)
    sender = _CapturingEmailSender()
    _use_email_sender(monkeypatch, sender)
    document_id = await _upload(client, headers)
    monkeypatch.setattr(settings, "max_email_attachments_mb", 0)

    resp = await client.post(
        "/api/v1/reports/share",
        headers=headers,
        json={"doctor_contact_id": doctor_id, "document_ids": [document_id]},
    )
    assert resp.status_code in (400, 422)
    assert "QR code" in resp.json()["error"]["message"]
    assert sender.sent == []


async def test_account_deletion_removes_shared_report_snapshots(client, unique_email):
    from app.storage.factory import get_storage_backend

    _, headers = await _setup_patient(client, unique_email)
    created = await _create_link(client, headers)
    async with AsyncSessionLocal() as session:
        link = await session.get(ReportShareLink, created["id"])
        assert link is not None and link.report_storage_path
        path = link.report_storage_path
    storage = get_storage_backend()
    assert await storage.exists(storage_path=path)

    resp = await client.post(
        "/api/v1/account/delete",
        headers=headers,
        json={"password": "SuperSecret123", "confirmation": "DELETE"},
    )
    assert resp.status_code in (200, 204), resp.text
    assert not await storage.exists(storage_path=path)


async def test_doctor_display_name_does_not_double_the_title():
    from app.utils.names import doctor_display_name

    assert doctor_display_name("Dr. Maya Gurung") == "Dr. Maya Gurung"
    assert doctor_display_name("Maya Gurung") == "Dr. Maya Gurung"
