import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_create_list_update_delete_allergy(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    create_resp = await client.post(
        "/api/v1/allergies",
        headers=headers,
        json={"name": "Penicillin", "severity": "severe", "reaction": "Hives"},
    )
    assert create_resp.status_code == 201, create_resp.text
    allergy_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/allergies", headers=headers)
    assert len(list_resp.json()) == 1

    update_resp = await client.put(
        f"/api/v1/allergies/{allergy_id}",
        headers=headers,
        json={"name": "Penicillin", "severity": "moderate"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["severity"] == "moderate"

    delete_resp = await client.delete(f"/api/v1/allergies/{allergy_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/allergies/{allergy_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_allergies_requires_authentication(client):
    resp = await client.get("/api/v1/allergies")
    assert resp.status_code in (401, 403)


async def test_allergy_validation_rejects_invalid_severity(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.post(
        "/api/v1/allergies", headers=headers, json={"name": "Latex", "severity": "extreme"}
    )
    assert resp.status_code == 422


async def test_users_cannot_see_each_others_allergies(client, unique_email):
    user_a = await register_and_login(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    create_resp = await client.post(
        "/api/v1/allergies", headers=headers_a, json={"name": "Peanuts"}
    )
    allergy_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/allergies/{allergy_id}", headers=headers_b)
    assert get_resp.status_code == 404
    assert (
        await client.put(
            f"/api/v1/allergies/{allergy_id}", headers=headers_b, json={"name": "Hacked"}
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/allergies/{allergy_id}", headers=headers_b)
    ).status_code == 404
    assert (await client.get("/api/v1/allergies", headers=headers_b)).json() == []
