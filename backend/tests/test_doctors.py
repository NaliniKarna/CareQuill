import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_create_list_update_delete_doctor(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    create_resp = await client.post(
        "/api/v1/doctors",
        headers=headers,
        json={
            "name": "Dr. Shrestha",
            "email": "shrestha@example.com",
            "specialization": "Cardiology",
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    doctor_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/doctors", headers=headers)
    assert len(list_resp.json()) == 1

    update_resp = await client.put(
        f"/api/v1/doctors/{doctor_id}",
        headers=headers,
        json={"name": "Dr. Shrestha", "clinic_name": "City Hospital"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["clinic_name"] == "City Hospital"

    delete_resp = await client.delete(f"/api/v1/doctors/{doctor_id}", headers=headers)
    assert delete_resp.status_code == 204


async def test_doctors_requires_authentication(client):
    resp = await client.get("/api/v1/doctors")
    assert resp.status_code in (401, 403)


async def test_doctor_validation_rejects_invalid_email(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.post(
        "/api/v1/doctors", headers=headers, json={"name": "Dr. X", "email": "not-an-email"}
    )
    assert resp.status_code == 422


async def test_users_cannot_see_each_others_doctors(client, unique_email):
    user_a = await register_and_login(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    create_resp = await client.post(
        "/api/v1/doctors", headers=headers_a, json={"name": "Dr. Private"}
    )
    doctor_id = create_resp.json()["id"]

    assert (
        await client.get(f"/api/v1/doctors/{doctor_id}", headers=headers_b)
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/doctors/{doctor_id}", headers=headers_b)
    ).status_code == 404
    assert (await client.get("/api/v1/doctors", headers=headers_b)).json() == []


@pytest.mark.parametrize(
    "phone",
    ["+977 9812345678", "9812345678", "01-4412345", "(977) 98-1234-5678"],
)
async def test_doctor_accepts_valid_phone_numbers(client, unique_email, phone):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    body = {"name": "Dr. P", "phone": phone}
    resp = await client.post("/api/v1/doctors", headers=headers, json=body)
    assert resp.status_code == 201
    assert resp.json()["phone"] == phone


@pytest.mark.parametrize("phone", ["abc", "12345", "98123x4567", "+" + "9" * 16, "98+12345678"])
async def test_doctor_rejects_invalid_phone_numbers(client, unique_email, phone):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    body = {"name": "Dr. P", "phone": phone}
    resp = await client.post("/api/v1/doctors", headers=headers, json=body)
    assert resp.status_code == 422


async def test_doctor_blank_phone_is_stored_as_empty(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    body = {"name": "Dr. P", "phone": "  "}
    resp = await client.post("/api/v1/doctors", headers=headers, json=body)
    assert resp.status_code == 201
    assert resp.json()["phone"] is None
