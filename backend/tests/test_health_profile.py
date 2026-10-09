import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_get_profile_before_creation_returns_404(client, unique_email):
    data = await register_and_login(client, unique_email)
    resp = await client.get("/api/v1/profile", headers=_auth_headers(data["access_token"]))
    assert resp.status_code == 404


async def test_profile_requires_authentication(client):
    resp = await client.get("/api/v1/profile")
    assert resp.status_code in (401, 403)


async def test_create_and_fetch_profile(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    put_resp = await client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "first_name": "Nalini",
            "last_name": "Karna",
            "gender": "female",
            "blood_group": "O+",
            "phone": "+9779800000000",
            "height": 165.5,
            "weight": 58.2,
        },
    )
    assert put_resp.status_code == 200
    body = put_resp.json()
    assert body["first_name"] == "Nalini"
    assert body["user_id"] == data["user"]["id"]

    get_resp = await client.get("/api/v1/profile", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["last_name"] == "Karna"


async def test_updating_profile_upserts_rather_than_duplicating(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    await client.put(
        "/api/v1/profile", headers=headers, json={"first_name": "Nalini", "last_name": "Karna"}
    )
    resp = await client.put(
        "/api/v1/profile", headers=headers, json={"first_name": "Nalini", "last_name": "K."}
    )
    assert resp.status_code == 200
    assert resp.json()["last_name"] == "K."

    get_resp = await client.get("/api/v1/profile", headers=headers)
    assert get_resp.json()["last_name"] == "K."


async def test_profile_validation_rejects_missing_required_fields(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.put("/api/v1/profile", headers=headers, json={"first_name": "Only"})
    assert resp.status_code == 422


async def test_users_cannot_see_each_others_profile(client, unique_email):
    """IDOR check: user B must never see user A's health profile, even
    though both hit the exact same endpoint."""
    user_a = await register_and_login(client, unique_email)
    user_b_email = f"b-{unique_email}"
    user_b = await register_and_login(client, user_b_email)

    await client.put(
        "/api/v1/profile",
        headers=_auth_headers(user_a["access_token"]),
        json={"first_name": "Alice", "last_name": "A"},
    )

    # User B has not created a profile yet, so B must get 404 - never A's data.
    resp = await client.get("/api/v1/profile", headers=_auth_headers(user_b["access_token"]))
    assert resp.status_code == 404

    resp_a = await client.get("/api/v1/profile", headers=_auth_headers(user_a["access_token"]))
    assert resp_a.status_code == 200
    assert resp_a.json()["first_name"] == "Alice"


@pytest.mark.parametrize("field", ["phone", "emergency_contact_phone"])
async def test_profile_rejects_invalid_phone_numbers(client, unique_email, field):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    body = {"first_name": "A", "last_name": "B", field: "not-a-phone"}
    resp = await client.put("/api/v1/profile", headers=headers, json=body)
    assert resp.status_code == 422


async def test_profile_accepts_valid_phone_numbers(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    body = {
        "first_name": "A",
        "last_name": "B",
        "phone": "+977 9812345678",
        "emergency_contact_phone": "01-4412345",
    }
    resp = await client.put("/api/v1/profile", headers=headers, json=body)
    assert resp.status_code == 200
    assert resp.json()["phone"] == "+977 9812345678"
    assert resp.json()["emergency_contact_phone"] == "01-4412345"
