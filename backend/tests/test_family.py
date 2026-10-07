"""Family circle: profiles, documents, invite/claim hand-over, access choice, sharing."""
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.family_member import FamilyMember
from tests.conftest import register_and_login
from tests.test_health_reports import (
    _CapturingEmailSender,
    _create_doctor,
    _setup_patient,
)

pytestmark = pytest.mark.asyncio

PDF = b"%PDF-1.4 family file"


@pytest.fixture(autouse=True)
def _capture_email(monkeypatch):
    sender = _CapturingEmailSender()
    from app.services import family_service

    monkeypatch.setattr(family_service, "get_email_sender", lambda: sender)
    return sender


async def _member(client, headers, name="Maya Karna", relation="parent") -> dict:
    resp = await client.post(
        "/api/v1/family/members",
        headers=headers,
        json={"full_name": name, "relation": relation, "blood_group": "O+"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _upload(client, headers, member_id, title="Blood test", filename="r.pdf"):
    return await client.post(
        f"/api/v1/family/members/{member_id}/documents",
        headers=headers,
        data={"title": title, "category": "blood_test"},
        files={"file": (filename, PDF, "application/pdf")},
    )


async def _second_user(client, unique_email, label="relative"):
    data = await register_and_login(client, f"{label}-{unique_email}")
    return {"Authorization": f"Bearer {data['access_token']}"}


async def _invite(client, headers, member_id) -> str:
    resp = await client.post(f"/api/v1/family/members/{member_id}/invite", headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["code"]


async def test_create_list_update_and_delete_profile(client, unique_email):
    _, headers = await _setup_patient(client, unique_email)
    member = await _member(client, headers)
    assert member["link_status"] == "unlinked"
    assert member["document_count"] == 0

    listed = (await client.get("/api/v1/family/members", headers=headers)).json()
    assert [m["id"] for m in listed] == [member["id"]]

    patched = await client.patch(
        f"/api/v1/family/members/{member['id']}", headers=headers, json={"notes": "Diabetic diet"}
    )
    assert patched.status_code == 200 and patched.json()["notes"] == "Diabetic diet"

    bad = await client.post(
        "/api/v1/family/members",
        headers=headers,
        json={"full_name": "  ", "relation": "parent"},
    )
    assert bad.status_code == 422

    deleted = await client.delete(f"/api/v1/family/members/{member['id']}", headers=headers)
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/family/members", headers=headers)).json() == []


async def test_profiles_and_documents_are_private_to_their_owner(client, unique_email):
    _, owner = await _setup_patient(client, unique_email)
    member = await _member(client, owner)
    doc = (await _upload(client, owner, member["id"])).json()
    other = await _second_user(client, unique_email, "stranger")

    base = f"/api/v1/family/members/{member['id']}"
    assert (await client.get("/api/v1/family/members", headers=other)).json() == []
    assert (await client.get(base, headers=other)).status_code == 404
    assert (await client.get(f"{base}/documents", headers=other)).status_code == 404
    assert (
        await client.get(f"{base}/documents/{doc['id']}/download", headers=other)
    ).status_code == 404
    assert (await client.delete(base, headers=other)).status_code == 404
    assert (await client.post(f"{base}/invite", headers=other)).status_code == 404
    assert (
        await client.post(
            f"{base}/share",
            headers=other,
            json={"document_ids": [doc["id"]], "recipient_email": "a@b.co"},
        )
    ).status_code == 404

    unauth = await client.get("/api/v1/family/members")
    assert unauth.status_code in (401, 403)


async def test_documents_are_validated_and_do_not_leak_into_my_own_records(client, unique_email):
    _, headers = await _setup_patient(client, unique_email)
    member = await _member(client, headers)

    resp = await _upload(client, headers, member["id"])
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["source"] == "family" and body["can_delete"] is True
    assert "storage_path" not in body

    bad_type = await client.post(
        f"/api/v1/family/members/{member['id']}/documents",
        headers=headers,
        data={"title": "x"},
        files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
    )
    assert bad_type.status_code == 422

    # A relative's file never appears among my own medical documents.
    mine = (await client.get("/api/v1/documents", headers=headers)).json()
    assert mine["total"] == 0

    download = await client.get(
        f"/api/v1/family/members/{member['id']}/documents/{body['id']}/download", headers=headers
    )
    assert download.status_code == 200 and download.content == PDF

    deleted = await client.delete(
        f"/api/v1/family/members/{member['id']}/documents/{body['id']}", headers=headers
    )
    assert deleted.status_code == 204
    assert (await client.get(f"/api/v1/family/members/{member['id']}", headers=headers)).json()[
        "document_count"
    ] == 0


async def test_invite_code_is_hashed_single_use_and_expires(client, unique_email):
    _, manager = await _setup_patient(client, unique_email)
    member = await _member(client, manager)
    code = await _invite(client, manager, member["id"])
    assert code.startswith("CQ-")

    async with AsyncSessionLocal() as session:
        row = (await session.execute(select(FamilyMember))).scalars().one()
        assert row.invite_code_hash and code not in row.invite_code_hash
        assert len(row.invite_code_hash) == 64

    # Cannot claim your own profile.
    own = await client.post("/api/v1/family/claim", headers=manager, json={"code": code})
    assert own.status_code == 422

    relative = await _second_user(client, unique_email)
    wrong = await client.post(
        "/api/v1/family/claim", headers=relative, json={"code": "CQ-AAAAA-BBBBB"}
    )
    assert wrong.status_code == 422

    ok = await client.post("/api/v1/family/claim", headers=relative, json={"code": code.lower()})
    assert ok.status_code == 200, ok.text
    assert ok.json()["link_status"] == "pending"

    # Single use.
    third = await _second_user(client, unique_email, "third")
    again = await client.post("/api/v1/family/claim", headers=third, json={"code": code})
    assert again.status_code == 422


async def test_expired_and_revoked_invites_are_rejected(client, unique_email, monkeypatch):
    _, manager = await _setup_patient(client, unique_email)
    member = await _member(client, manager)
    relative = await _second_user(client, unique_email)

    code = await _invite(client, manager, member["id"])
    revoked = await client.delete(f"/api/v1/family/members/{member['id']}/invite", headers=manager)
    assert revoked.status_code == 204
    resp = await client.post("/api/v1/family/claim", headers=relative, json={"code": code})
    assert resp.status_code == 422

    from datetime import UTC, datetime, timedelta

    code = await _invite(client, manager, member["id"])
    async with AsyncSessionLocal() as session:
        row = (await session.execute(select(FamilyMember))).scalars().one()
        row.invite_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()
    resp = await client.post("/api/v1/family/claim", headers=relative, json={"code": code})
    assert resp.status_code == 422


async def test_claim_moves_documents_and_manager_loses_access_until_person_decides(
    client, unique_email
):
    _, manager = await _setup_patient(client, unique_email)
    member = await _member(client, manager)
    await _upload(client, manager, member["id"], title="Old report")
    code = await _invite(client, manager, member["id"])
    relative = await _second_user(client, unique_email)

    claimed = await client.post("/api/v1/family/claim", headers=relative, json={"code": code})
    assert claimed.status_code == 200
    assert claimed.json()["manager_name"] == "Jane Doe"

    # The documents are now in the relative's own account.
    mine = (await client.get("/api/v1/documents", headers=relative)).json()
    assert [d["title"] for d in mine["items"]] == ["Old report"]

    # Pending: the manager sees the profile but not the documents.
    profile = (await client.get(f"/api/v1/family/members/{member['id']}", headers=manager)).json()
    assert profile["link_status"] == "pending" and profile["document_count"] is None
    base = f"/api/v1/family/members/{member['id']}"
    assert (await client.get(f"{base}/documents", headers=manager)).status_code == 403
    assert (await _upload(client, manager, member["id"])).status_code == 403
    # ...and can no longer edit the person's details.
    assert (
        await client.patch(base, headers=manager, json={"notes": "x"})
    ).status_code == 403


async def test_person_keeps_manager_as_helper_who_can_view_upload_and_share_but_not_delete(
    client, unique_email, _capture_email
):
    _, manager = await _setup_patient(client, unique_email)
    member = await _member(client, manager)
    await _upload(client, manager, member["id"], title="Old report")
    code = await _invite(client, manager, member["id"])
    relative = await _second_user(client, unique_email)
    await client.post("/api/v1/family/claim", headers=relative, json={"code": code})

    decided = await client.post(
        f"/api/v1/family/linked-to-me/{member['id']}/access",
        headers=relative,
        json={"allow": True},
    )
    assert decided.status_code == 200 and decided.json()["link_status"] == "active"

    base = f"/api/v1/family/members/{member['id']}"
    docs = (await client.get(f"{base}/documents", headers=manager)).json()
    assert [d["title"] for d in docs] == ["Old report"]
    assert docs[0]["source"] == "account" and docs[0]["can_delete"] is False

    # Helper upload lands in the person's own account.
    up = await _upload(client, manager, member["id"], title="New scan")
    assert up.status_code == 201 and up.json()["source"] == "account"
    mine = (await client.get("/api/v1/documents", headers=relative)).json()
    assert {d["title"] for d in mine["items"]} == {"Old report", "New scan"}

    # Helper cannot delete.
    deleted = await client.delete(f"{base}/documents/{docs[0]['id']}", headers=manager)
    assert deleted.status_code == 403

    # Helper can share to a doctor.
    doctor_id = await _create_doctor(client, manager)
    shared = await client.post(
        f"{base}/share",
        headers=manager,
        json={
            "document_ids": [docs[0]["id"]],
            "doctor_contact_id": doctor_id,
            "message": "Please review",
        },
    )
    assert shared.status_code == 200, shared.text
    assert shared.json()["status"] == "sent"
    message = _capture_email.sent[-1]
    assert message.to == "patel@example.com"
    assert message.reply_to
    names = [a[0] for a in message.attachments]
    assert "r.pdf" in names and any(n.startswith("health-summary") for n in names)

    # The person is told, and can later end access at any time.
    notes = (await client.get("/api/v1/notifications", headers=relative)).json()
    assert any(n["type"] == "family_update" for n in notes)
    ended = await client.post(
        f"/api/v1/family/linked-to-me/{member['id']}/access",
        headers=relative,
        json={"allow": False},
    )
    assert ended.json()["link_status"] == "ended"
    assert (await client.get(f"{base}/documents", headers=manager)).status_code == 403
    assert (
        await client.get(f"{base}/documents/{docs[0]['id']}/download", headers=manager)
    ).status_code == 403
    # The person's own documents are untouched.
    assert (await client.get("/api/v1/documents", headers=relative)).json()["total"] == 2


async def test_only_the_linked_person_can_decide_access(client, unique_email):
    _, manager = await _setup_patient(client, unique_email)
    member = await _member(client, manager)
    code = await _invite(client, manager, member["id"])
    relative = await _second_user(client, unique_email)
    await client.post("/api/v1/family/claim", headers=relative, json={"code": code})

    # The manager cannot approve their own access, nor can a stranger.
    url = f"/api/v1/family/linked-to-me/{member['id']}/access"
    assert (await client.post(url, headers=manager, json={"allow": True})).status_code == 404
    stranger = await _second_user(client, unique_email, "stranger")
    assert (await client.post(url, headers=stranger, json={"allow": True})).status_code == 404
    assert (await client.get("/api/v1/family/linked-to-me", headers=stranger)).json() == []
    assert len((await client.get("/api/v1/family/linked-to-me", headers=relative)).json()) == 1


async def test_a_person_cannot_use_another_documents_through_the_family_endpoints(
    client, unique_email
):
    """A helper only reaches the linked person's documents, never anyone else's."""
    _, manager = await _setup_patient(client, unique_email)
    member = await _member(client, manager)
    code = await _invite(client, manager, member["id"])
    relative = await _second_user(client, unique_email)
    await client.post("/api/v1/family/claim", headers=relative, json={"code": code})
    await client.post(
        f"/api/v1/family/linked-to-me/{member['id']}/access",
        headers=relative,
        json={"allow": True},
    )
    # A document that belongs to the manager personally.
    mine = await client.post(
        "/api/v1/documents",
        headers=manager,
        data={"title": "My own"},
        files={"file": ("m.pdf", PDF, "application/pdf")},
    )
    own_id = mine.json()["id"]
    base = f"/api/v1/family/members/{member['id']}"
    stray = await client.get(f"{base}/documents/{own_id}/download", headers=manager)
    assert stray.status_code == 404
    shared = await client.post(
        f"{base}/share",
        headers=manager,
        json={"document_ids": [own_id], "recipient_email": "x@example.com"},
    )
    assert shared.status_code == 404


async def test_share_needs_a_recipient_and_respects_size_limit(
    client, unique_email, monkeypatch
):
    _, headers = await _setup_patient(client, unique_email)
    member = await _member(client, headers)
    doc = (await _upload(client, headers, member["id"])).json()
    base = f"/api/v1/family/members/{member['id']}"

    none = await client.post(f"{base}/share", headers=headers, json={"document_ids": [doc["id"]]})
    assert none.status_code == 422

    monkeypatch.setattr(settings, "max_email_attachments_mb", 0)
    big = await client.post(
        f"{base}/share",
        headers=headers,
        json={"document_ids": [doc["id"]], "recipient_email": "me@example.com"},
    )
    assert big.status_code == 422
    monkeypatch.setattr(settings, "max_email_attachments_mb", 20)

    ok = await client.post(
        f"{base}/share",
        headers=headers,
        json={
            "document_ids": [doc["id"]],
            "recipient_email": "me@example.com",
            "recipient_name": "Maya",
        },
    )
    assert ok.status_code == 200 and ok.json()["recipient_email"] == "me@example.com"
    history = (await client.get(f"{base}/shares", headers=headers)).json()
    assert history[0]["document_titles"] == ["Blood test"]


async def test_member_limit_is_enforced(client, unique_email, monkeypatch):
    _, headers = await _setup_patient(client, unique_email)
    monkeypatch.setattr(settings, "family_max_members", 1)
    await _member(client, headers)
    again = await client.post(
        "/api/v1/family/members", headers=headers, json={"full_name": "Two", "relation": "child"}
    )
    assert again.status_code == 422


async def test_export_and_delete_account_include_family_data(client, unique_email):
    from app.storage.factory import get_storage_backend

    _, headers = await _setup_patient(client, unique_email)
    member = await _member(client, headers)
    doc = (await _upload(client, headers, member["id"])).json()
    async with AsyncSessionLocal() as session:
        from app.models.family_member import FamilyDocument

        path = (await session.execute(select(FamilyDocument.storage_path))).scalars().one()
    storage = get_storage_backend()
    assert await storage.exists(storage_path=path)

    export = await client.get("/api/v1/account/export", headers=headers)
    assert export.status_code == 200
    import io
    import json
    import zipfile

    archive = zipfile.ZipFile(io.BytesIO(export.content))
    data = json.loads(archive.read("data.json"))
    assert data["family_members"][0]["full_name"] == "Maya Karna"
    assert "invite_code_hash" not in data["family_members"][0]
    assert any(name.startswith("family_documents/") for name in archive.namelist())
    assert data["family_documents"][0]["id"] == doc["id"]

    gone = await client.post(
        "/api/v1/account/delete",
        headers=headers,
        json={"password": "SuperSecret123", "confirmation": "DELETE"},
    )
    assert gone.status_code in (200, 204), gone.text
    assert not await storage.exists(storage_path=path)
