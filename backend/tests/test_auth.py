import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


async def test_register_creates_user_and_returns_tokens(client, unique_email):
    data = await register_and_login(client, unique_email)
    assert data["user"]["email"] == unique_email
    assert data["user"]["is_verified"] is False
    assert data["access_token"]
    assert data["refresh_token"]


async def test_register_rejects_short_password(client, unique_email):
    resp = await client.post(
        "/api/v1/auth/register", json={"email": unique_email, "password": "short"}
    )
    assert resp.status_code == 422


async def test_register_duplicate_email_conflicts(client, unique_email):
    await register_and_login(client, unique_email)
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": "AnotherPass123"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "conflict"


async def test_login_success(client, unique_email):
    await register_and_login(client, unique_email, password="SuperSecret123")
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "SuperSecret123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password_fails(client, unique_email):
    await register_and_login(client, unique_email, password="SuperSecret123")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "WrongPassword"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


async def test_login_unknown_email_fails(client, unique_email):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "whatever123"}
    )
    assert resp.status_code == 401


async def test_get_me_requires_authentication(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)


async def test_get_me_returns_current_user(client, unique_email):
    data = await register_and_login(client, unique_email)
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == unique_email


async def test_get_me_rejects_garbage_token(client):
    resp = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


async def test_refresh_rotates_token_and_invalidates_old_one(client, unique_email):
    data = await register_and_login(client, unique_email)
    old_refresh = data["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != old_refresh

    # The rotated-out token must no longer work.
    reuse_resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse_resp.status_code == 401

    # The new refresh token does work.
    again_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert again_resp.status_code == 200


async def test_refresh_rejects_unknown_token(client):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "totally-made-up"})
    assert resp.status_code == 401


async def test_logout_revokes_refresh_token(client, unique_email):
    data = await register_and_login(client, unique_email)
    logout_resp = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": data["refresh_token"]}
    )
    assert logout_resp.status_code == 200

    reuse_resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": data["refresh_token"]}
    )
    assert reuse_resp.status_code == 401


async def test_forgot_password_does_not_reveal_account_existence(client, unique_email):
    resp_known = await client.post("/api/v1/auth/forgot-password", json={"email": unique_email})
    resp_unknown = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody-here@example.com"}
    )
    assert resp_known.status_code == 200
    assert resp_unknown.status_code == 200
    assert resp_known.json() == resp_unknown.json()


async def test_reset_password_with_invalid_token_fails(client):
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "bogus-token", "new_password": "BrandNewPass123"},
    )
    assert resp.status_code == 422


async def test_verify_email_with_invalid_token_fails(client):
    resp = await client.post("/api/v1/auth/verify-email", json={"token": "bogus-token"})
    assert resp.status_code == 422


async def test_password_is_never_returned(client, unique_email):
    data = await register_and_login(client, unique_email)
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


# -- change password ----------------------------------------------------------


async def test_change_password_requires_authentication(client):
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "whatever", "new_password": "NewPassword123"},
    )
    assert resp.status_code in (401, 403)


async def test_change_password_rejects_wrong_current_password(client, unique_email):
    data = await register_and_login(client, unique_email, password="SuperSecret123")
    headers = {"Authorization": f"Bearer {data['access_token']}"}

    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "WrongCurrentPassword", "new_password": "BrandNewPass123"},
    )
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["code"] == "unauthorized"

    # The old password must still work -- nothing was changed.
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "SuperSecret123"},
    )
    assert login_resp.status_code == 200


async def test_change_password_succeeds_and_revokes_other_sessions(client, unique_email):
    data = await register_and_login(client, unique_email, password="SuperSecret123")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    old_refresh_token = data["refresh_token"]

    # A second, separate login session for the same user.
    second_login = await client.post(
        "/api/v1/auth/login",
        json={"email": unique_email, "password": "SuperSecret123"},
    )
    assert second_login.status_code == 200
    second_refresh_token = second_login.json()["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "SuperSecret123", "new_password": "BrandNewPass123"},
    )
    assert resp.status_code == 200, resp.text

    # Both this session's and the other session's refresh tokens are revoked.
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
    ).status_code == 401
    assert (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": second_refresh_token})
    ).status_code == 401

    # The old password no longer works; the new one does.
    assert (
        await client.post(
            "/api/v1/auth/login", json={"email": unique_email, "password": "SuperSecret123"}
        )
    ).status_code == 401
    assert (
        await client.post(
            "/api/v1/auth/login", json={"email": unique_email, "password": "BrandNewPass123"}
        )
    ).status_code == 200


async def test_change_password_rejects_short_new_password(client, unique_email):
    data = await register_and_login(client, unique_email, password="SuperSecret123")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "SuperSecret123", "new_password": "short"},
    )
    assert resp.status_code == 422
