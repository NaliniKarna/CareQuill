import uuid

import pytest
from sqlalchemy import select

from app.models.ai_summary import AISummary
from tests.conftest import TestSessionLocal, register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_generate_snapshot_creates_version_1(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    resp = await client.post("/api/v1/health-snapshots/generate", headers=headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["version"] == 1
    assert body["snapshot_data"]["medications"] == []


async def test_creating_a_medication_auto_generates_a_snapshot(client, unique_email):
    """Snapshots must be regenerated automatically, not only via the
    explicit /generate endpoint."""
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    latest_before = await client.get("/api/v1/health-snapshots/latest", headers=headers)
    assert latest_before.status_code == 404

    await client.post("/api/v1/medications", headers=headers, json={"name": "Metformin"})

    latest_after = await client.get("/api/v1/health-snapshots/latest", headers=headers)
    assert latest_after.status_code == 200
    assert latest_after.json()["version"] == 1
    assert latest_after.json()["snapshot_data"]["medications"][0]["name"] == "Metformin"


async def test_generate_increments_version_and_lists_lightweight(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    await client.post("/api/v1/health-snapshots/generate", headers=headers)
    second = await client.post("/api/v1/health-snapshots/generate", headers=headers)
    assert second.json()["version"] == 2

    list_resp = await client.get("/api/v1/health-snapshots", headers=headers)
    assert list_resp.status_code == 200
    versions = [item["version"] for item in list_resp.json()]
    assert versions == [2, 1]
    # Lightweight listing must not include the full blob.
    assert "snapshot_data" not in list_resp.json()[0]


async def test_generating_a_snapshot_marks_old_ai_summaries_outdated(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    patient_id = uuid.UUID(data["user"]["id"])

    snapshot_resp = await client.post("/api/v1/health-snapshots/generate", headers=headers)
    snapshot_id = uuid.UUID(snapshot_resp.json()["id"])

    async with TestSessionLocal() as session:
        pending = AISummary(
            patient_id=patient_id,
            health_snapshot_id=snapshot_id,
            summary_text="A summary",
            model_name="test-model",
            prompt_version="v1",
            status="pending_review",
        )
        shared = AISummary(
            patient_id=patient_id,
            health_snapshot_id=snapshot_id,
            summary_text="A shared summary",
            model_name="test-model",
            prompt_version="v1",
            status="shared",
        )
        session.add_all([pending, shared])
        await session.commit()
        pending_id, shared_id = pending.id, shared.id

    await client.post("/api/v1/health-snapshots/generate", headers=headers)

    async with TestSessionLocal() as session:
        result = await session.execute(select(AISummary).where(AISummary.id == pending_id))
        assert result.scalar_one().status == "outdated"
        result = await session.execute(select(AISummary).where(AISummary.id == shared_id))
        # "shared" history is immutable -- never touched.
        assert result.scalar_one().status == "shared"


async def test_health_snapshots_requires_authentication(client):
    resp = await client.get("/api/v1/health-snapshots")
    assert resp.status_code in (401, 403)


async def test_users_cannot_see_each_others_snapshots(client, unique_email):
    user_a = await register_and_login(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    snapshot_resp = await client.post("/api/v1/health-snapshots/generate", headers=headers_a)
    snapshot_id = snapshot_resp.json()["id"]

    resp = await client.get(f"/api/v1/health-snapshots/{snapshot_id}", headers=headers_b)
    assert resp.status_code == 404

    latest_resp = await client.get("/api/v1/health-snapshots/latest", headers=headers_b)
    assert latest_resp.status_code == 404
