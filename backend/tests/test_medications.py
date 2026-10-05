import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_create_and_list_medications(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    resp = await client.post(
        "/api/v1/medications",
        headers=headers,
        json={"name": "Metformin", "dosage": "500 mg", "frequency": "twice daily"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Metformin"
    assert body["is_active"] is True

    list_resp = await client.get("/api/v1/medications", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


async def test_medications_requires_authentication(client):
    resp = await client.get("/api/v1/medications")
    assert resp.status_code in (401, 403)


async def test_medication_validation_rejects_end_before_start(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.post(
        "/api/v1/medications",
        headers=headers,
        json={"name": "Aspirin", "start_date": "2026-05-01", "end_date": "2026-04-01"},
    )
    assert resp.status_code == 422


async def test_medication_validation_rejects_missing_name(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.post("/api/v1/medications", headers=headers, json={"name": ""})
    assert resp.status_code == 422


async def test_activate_and_deactivate_medication(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    create_resp = await client.post(
        "/api/v1/medications", headers=headers, json={"name": "Ibuprofen"}
    )
    med_id = create_resp.json()["id"]

    deactivate_resp = await client.patch(
        f"/api/v1/medications/{med_id}/deactivate", headers=headers
    )
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["is_active"] is False

    active_filter_resp = await client.get(
        "/api/v1/medications", headers=headers, params={"active": "true"}
    )
    assert active_filter_resp.json() == []

    activate_resp = await client.patch(f"/api/v1/medications/{med_id}/activate", headers=headers)
    assert activate_resp.status_code == 200
    assert activate_resp.json()["is_active"] is True


async def test_update_medication_does_not_accept_is_active(client, unique_email):
    """The generic PUT must not be a backdoor for toggling is_active --
    that's the whole reason dedicated /activate and /deactivate endpoints
    exist. Extra field is just ignored (Pydantic default), is_active must
    only ever change via the dedicated endpoints."""
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    create_resp = await client.post(
        "/api/v1/medications", headers=headers, json={"name": "Paracetamol"}
    )
    med_id = create_resp.json()["id"]

    await client.patch(f"/api/v1/medications/{med_id}/deactivate", headers=headers)

    put_resp = await client.put(
        f"/api/v1/medications/{med_id}",
        headers=headers,
        json={"name": "Paracetamol", "is_active": True},
    )
    assert put_resp.status_code == 200
    # is_active must remain False -- the PUT body's is_active is ignored.
    assert put_resp.json()["is_active"] is False


async def test_delete_medication(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    create_resp = await client.post(
        "/api/v1/medications", headers=headers, json={"name": "Vitamin D"}
    )
    med_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/medications/{med_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/medications/{med_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_users_cannot_see_or_modify_each_others_medications(client, unique_email):
    user_a = await register_and_login(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    create_resp = await client.post(
        "/api/v1/medications", headers=headers_a, json={"name": "Secret Med"}
    )
    med_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/medications/{med_id}", headers=headers_b)
    assert get_resp.status_code == 404

    update_resp = await client.put(
        f"/api/v1/medications/{med_id}", headers=headers_b, json={"name": "Hacked"}
    )
    assert update_resp.status_code == 404

    delete_resp = await client.delete(f"/api/v1/medications/{med_id}", headers=headers_b)
    assert delete_resp.status_code == 404

    list_resp = await client.get("/api/v1/medications", headers=headers_b)
    assert list_resp.json() == []


# --- Reminders -------------------------------------------------------------


async def test_create_and_list_reminders(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    med_resp = await client.post(
        "/api/v1/medications", headers=headers, json={"name": "Metformin"}
    )
    med_id = med_resp.json()["id"]

    create_resp = await client.post(
        f"/api/v1/medications/{med_id}/reminders",
        headers=headers,
        json={"reminder_time": "08:00:00", "days_of_week": "daily"},
    )
    assert create_resp.status_code == 201, create_resp.text
    assert create_resp.json()["days_of_week"] == "daily"

    list_resp = await client.get(f"/api/v1/medications/{med_id}/reminders", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


async def test_reminder_rejects_invalid_days_of_week(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    med_resp = await client.post(
        "/api/v1/medications", headers=headers, json={"name": "Metformin"}
    )
    med_id = med_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/medications/{med_id}/reminders",
        headers=headers,
        json={"reminder_time": "08:00:00", "days_of_week": "funday"},
    )
    assert resp.status_code == 422


async def test_reminder_requires_owned_medication(client, unique_email):
    user_a = await register_and_login(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    med_resp = await client.post(
        "/api/v1/medications", headers=headers_a, json={"name": "Metformin"}
    )
    med_id = med_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/medications/{med_id}/reminders",
        headers=headers_b,
        json={"reminder_time": "08:00:00", "days_of_week": "daily"},
    )
    assert resp.status_code == 404


async def test_update_and_delete_reminder(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    med_resp = await client.post(
        "/api/v1/medications", headers=headers, json={"name": "Metformin"}
    )
    med_id = med_resp.json()["id"]
    reminder_resp = await client.post(
        f"/api/v1/medications/{med_id}/reminders",
        headers=headers,
        json={"reminder_time": "08:00:00", "days_of_week": "mon,wed,fri"},
    )
    reminder_id = reminder_resp.json()["id"]

    update_resp = await client.patch(
        f"/api/v1/medications/{med_id}/reminders/{reminder_id}",
        headers=headers,
        json={"is_enabled": False},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["is_enabled"] is False

    delete_resp = await client.delete(
        f"/api/v1/medications/{med_id}/reminders/{reminder_id}", headers=headers
    )
    assert delete_resp.status_code == 204

    list_resp = await client.get(f"/api/v1/medications/{med_id}/reminders", headers=headers)
    assert list_resp.json() == []
