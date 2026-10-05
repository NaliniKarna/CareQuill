from datetime import date, timedelta

import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _future_date(days: int = 7) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _past_date(days: int = 7) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


async def test_create_and_list_appointment(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    create_resp = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={"appointment_date": _future_date(), "reason": "Checkup"},
    )
    assert create_resp.status_code == 201, create_resp.text
    assert create_resp.json()["status"] == "scheduled"

    upcoming_resp = await client.get(
        "/api/v1/appointments", headers=headers, params={"filter": "upcoming"}
    )
    assert len(upcoming_resp.json()) == 1

    past_resp = await client.get(
        "/api/v1/appointments", headers=headers, params={"filter": "past"}
    )
    assert past_resp.json() == []


async def test_appointments_requires_authentication(client):
    resp = await client.get("/api/v1/appointments")
    assert resp.status_code in (401, 403)


async def test_create_appointment_rejects_past_date(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={"appointment_date": _past_date(), "reason": "Old visit"},
    )
    assert resp.status_code == 422


async def test_create_appointment_with_unowned_doctor_contact_is_rejected(client, unique_email):
    """IDOR: attaching another patient's doctor_contact_id to your own
    appointment must fail, not silently succeed."""
    user_a = await register_and_login(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    doctor_resp = await client.post(
        "/api/v1/doctors", headers=headers_a, json={"name": "Dr. A's Doctor"}
    )
    doctor_id = doctor_resp.json()["id"]

    resp = await client.post(
        "/api/v1/appointments",
        headers=headers_b,
        json={
            "appointment_date": _future_date(),
            "doctor_contact_id": doctor_id,
            "reason": "Should fail",
        },
    )
    assert resp.status_code == 404


async def test_cancel_complete_miss_transitions(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    create_resp = await client.post(
        "/api/v1/appointments", headers=headers, json={"appointment_date": _future_date()}
    )
    appt_id = create_resp.json()["id"]

    cancel_resp = await client.patch(f"/api/v1/appointments/{appt_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Already terminal -- cannot transition again.
    complete_resp = await client.patch(
        f"/api/v1/appointments/{appt_id}/complete", headers=headers
    )
    assert complete_resp.status_code == 422

    create_resp_2 = await client.post(
        "/api/v1/appointments", headers=headers, json={"appointment_date": _future_date()}
    )
    appt_id_2 = create_resp_2.json()["id"]
    miss_resp = await client.patch(f"/api/v1/appointments/{appt_id_2}/miss", headers=headers)
    assert miss_resp.status_code == 200
    assert miss_resp.json()["status"] == "missed"


async def test_users_cannot_see_or_modify_each_others_appointments(client, unique_email):
    user_a = await register_and_login(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    create_resp = await client.post(
        "/api/v1/appointments", headers=headers_a, json={"appointment_date": _future_date()}
    )
    appt_id = create_resp.json()["id"]

    assert (
        await client.get(f"/api/v1/appointments/{appt_id}", headers=headers_b)
    ).status_code == 404
    assert (
        await client.patch(f"/api/v1/appointments/{appt_id}/cancel", headers=headers_b)
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/appointments/{appt_id}", headers=headers_b)
    ).status_code == 404
    assert (await client.get("/api/v1/appointments", headers=headers_b)).json() == []
