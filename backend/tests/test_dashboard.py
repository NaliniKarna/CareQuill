import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def test_dashboard_requires_authentication(client):
    resp = await client.get("/api/v1/dashboard")
    assert resp.status_code in (401, 403)


async def test_dashboard_defaults_for_new_user(client, unique_email):
    data = await register_and_login(client, unique_email)
    resp = await client.get(
        "/api/v1/dashboard", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_health_profile"] is False
    assert body["profile_completion_percent"] == 0
    assert body["active_medications_count"] == 0
    assert body["next_appointment"] is None
    assert body["health_snapshot_status"] == "not_generated"
    assert "Complete your health profile" in " ".join(body["notifications"])


async def test_dashboard_reflects_profile_completion(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    await client.put(
        "/api/v1/profile", headers=headers, json={"first_name": "Nalini", "last_name": "Karna"}
    )
    resp = await client.get("/api/v1/dashboard", headers=headers)
    body = resp.json()
    assert body["has_health_profile"] is True
    assert body["profile_completion_percent"] > 0
    assert body["welcome_message"].startswith("Welcome back, Nalini")
    assert body["reminders_due_today_count"] == 0


async def test_dashboard_counts_reminders_due_today_for_active_medications_only(
    client, unique_email
):
    import datetime

    data = await register_and_login(client, unique_email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    active_med = (
        await client.post("/api/v1/medications", headers=headers, json={"name": "Metformin"})
    ).json()
    inactive_med = (
        await client.post("/api/v1/medications", headers=headers, json={"name": "Ibuprofen"})
    ).json()
    await client.patch(
        f"/api/v1/medications/{inactive_med['id']}/deactivate", headers=headers
    )

    today_code = datetime.date.today().strftime("%a").lower()
    other_day = "sun" if today_code != "sun" else "sat"

    # Due today: enabled, on an active medication.
    await client.post(
        f"/api/v1/medications/{active_med['id']}/reminders",
        headers=headers,
        json={"reminder_time": "08:00:00", "days_of_week": today_code},
    )
    # Not due today: different day.
    await client.post(
        f"/api/v1/medications/{active_med['id']}/reminders",
        headers=headers,
        json={"reminder_time": "09:00:00", "days_of_week": other_day},
    )
    # Not due: disabled.
    disabled = (
        await client.post(
            f"/api/v1/medications/{active_med['id']}/reminders",
            headers=headers,
            json={"reminder_time": "10:00:00", "days_of_week": "daily"},
        )
    ).json()
    await client.patch(
        f"/api/v1/medications/{active_med['id']}/reminders/{disabled['id']}",
        headers=headers,
        json={"is_enabled": False},
    )
    # Not due: medication inactive, even though "daily".
    await client.post(
        f"/api/v1/medications/{inactive_med['id']}/reminders",
        headers=headers,
        json={"reminder_time": "11:00:00", "days_of_week": "daily"},
    )

    resp = await client.get("/api/v1/dashboard", headers=headers)
    assert resp.json()["reminders_due_today_count"] == 1


async def test_dashboard_next_appointment_includes_doctor_name(client, unique_email):
    import datetime

    data = await register_and_login(client, unique_email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    doctor = (
        await client.post(
            "/api/v1/doctors", headers=headers, json={"name": "Dr. Rao"}
        )
    ).json()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={"doctor_contact_id": doctor["id"], "appointment_date": tomorrow},
    )

    resp = await client.get("/api/v1/dashboard", headers=headers)
    body = resp.json()
    assert body["next_appointment"]["doctor_name"] == "Dr. Rao"
