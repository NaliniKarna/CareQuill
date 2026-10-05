import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_timeline_aggregates_verified_and_patient_provided_entries(client, unique_email):
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
        json={"name": "Metformin", "start_date": "2023-06-01"},
    )
    await client.post(
        "/api/v1/timeline/notes",
        headers=headers,
        json={"note_text": "Felt better today", "event_date": "2024-01-01"},
    )

    resp = await client.get("/api/v1/timeline", headers=headers)
    assert resp.status_code == 200
    entries = resp.json()
    types = {e["type"] for e in entries}
    assert {"condition", "medication", "note"} <= types

    condition_entry = next(e for e in entries if e["type"] == "condition")
    assert condition_entry["tag"] == "VERIFIED"
    note_entry = next(e for e in entries if e["type"] == "note")
    assert note_entry["tag"] == "PATIENT_PROVIDED"

    # Sorted chronologically, most recent first.
    dates = [e["date"] for e in entries]
    assert dates == sorted(dates, reverse=True)


async def test_timeline_filters_by_type_and_date_range(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    await client.post(
        "/api/v1/conditions",
        headers=headers,
        json={"name": "Asthma", "diagnosed_date": "2022-01-15"},
    )
    await client.post(
        "/api/v1/timeline/notes",
        headers=headers,
        json={"note_text": "Note", "event_date": "2024-01-01"},
    )

    type_resp = await client.get(
        "/api/v1/timeline", headers=headers, params={"type": "note"}
    )
    assert all(e["type"] == "note" for e in type_resp.json())

    range_resp = await client.get(
        "/api/v1/timeline",
        headers=headers,
        params={"date_from": "2023-01-01", "date_to": "2024-12-31"},
    )
    assert all("2023-01-01" <= e["date"] <= "2024-12-31" for e in range_resp.json())


async def test_timeline_requires_authentication(client):
    resp = await client.get("/api/v1/timeline")
    assert resp.status_code in (401, 403)


async def test_timeline_notes_crud_and_idor(client, unique_email):
    user_a = await register_and_login(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    create_resp = await client.post(
        "/api/v1/timeline/notes",
        headers=headers_a,
        json={"note_text": "Private note", "event_date": "2024-01-01"},
    )
    assert create_resp.status_code == 201
    note_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/timeline/notes", headers=headers_a)
    assert len(list_resp.json()) == 1

    # User B cannot see or delete user A's note.
    b_list_resp = await client.get("/api/v1/timeline/notes", headers=headers_b)
    assert b_list_resp.json() == []

    b_delete_resp = await client.delete(f"/api/v1/timeline/notes/{note_id}", headers=headers_b)
    assert b_delete_resp.status_code == 404

    a_delete_resp = await client.delete(f"/api/v1/timeline/notes/{note_id}", headers=headers_a)
    assert a_delete_resp.status_code == 204


async def test_timeline_note_validation_rejects_empty_text(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.post(
        "/api/v1/timeline/notes",
        headers=headers,
        json={"note_text": "", "event_date": "2024-01-01"},
    )
    assert resp.status_code == 422
