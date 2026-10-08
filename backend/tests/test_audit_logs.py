import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_audit_logs_requires_authentication(client):
    resp = await client.get("/api/v1/audit-logs")
    assert resp.status_code in (401, 403)


async def test_audit_log_records_login_and_medication_create(client, unique_email):
    data = await register_and_login(client, unique_email, password="SuperSecret#123")
    headers = _auth_headers(data["access_token"])

    # register_and_login only registers -- log in explicitly to record a
    # `login` event too.
    await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "SuperSecret#123"}
    )
    await client.post("/api/v1/medications", headers=headers, json={"name": "Metformin"})

    resp = await client.get("/api/v1/audit-logs", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    event_types = {item["event_type"] for item in body["items"]}
    assert "login" in event_types
    assert "medication_create" in event_types
    # Never leaks medical content or credentials -- only ids/types.
    for item in body["items"]:
        assert "password" not in item
        assert "token" not in item


async def test_users_only_see_their_own_audit_logs(client, unique_email):
    user_a = await register_and_login(client, unique_email, password="SuperSecret#123")
    headers_a = _auth_headers(user_a["access_token"])
    await client.post("/api/v1/medications", headers=headers_a, json={"name": "Metformin"})

    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_b = _auth_headers(user_b["access_token"])

    resp_b = await client.get("/api/v1/audit-logs", headers=headers_b)
    event_types_b = {item["event_type"] for item in resp_b.json()["items"]}
    assert "medication_create" not in event_types_b
