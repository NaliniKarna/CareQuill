from datetime import date, timedelta

import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def test_journal_crud(client, unique_email):
    data = await register_and_login(client, unique_email)
    h = _h(data["access_token"])
    today = date.today().isoformat()

    created = await client.post(
        "/api/v1/journal",
        headers=h,
        json={"entry_date": today, "mood": 4, "title": "Good day", "body": "Walked 30 minutes."},
    )
    assert created.status_code == 201, created.text
    entry_id = created.json()["id"]

    listed = await client.get("/api/v1/journal", headers=h)
    assert listed.json()["total"] == 1

    updated = await client.put(
        f"/api/v1/journal/{entry_id}",
        headers=h,
        json={"entry_date": today, "mood": 2, "title": None, "body": "Headache in the evening."},
    )
    assert updated.status_code == 200
    assert updated.json()["mood"] == 2
    assert updated.json()["title"] is None

    assert (await client.delete(f"/api/v1/journal/{entry_id}", headers=h)).status_code == 204
    assert (await client.get(f"/api/v1/journal/{entry_id}", headers=h)).status_code == 404


async def test_journal_filters_and_search(client, unique_email):
    data = await register_and_login(client, unique_email)
    h = _h(data["access_token"])
    old = (date.today() - timedelta(days=20)).isoformat()
    for d, body in ((old, "knee pain after run"), (date.today().isoformat(), "slept well")):
        r = await client.post("/api/v1/journal", headers=h, json={"entry_date": d, "body": body})
        assert r.status_code == 201

    by_text = await client.get("/api/v1/journal", headers=h, params={"q": "knee"})
    assert by_text.json()["total"] == 1
    since = (date.today() - timedelta(days=5)).isoformat()
    recent = await client.get("/api/v1/journal", headers=h, params={"date_from": since})
    assert [e["body"] for e in recent.json()["items"]] == ["slept well"]


async def test_journal_validation(client, unique_email):
    data = await register_and_login(client, unique_email)
    h = _h(data["access_token"])
    today = date.today().isoformat()
    url = "/api/v1/journal"
    bad_mood = await client.post(url, headers=h, json={"entry_date": today, "mood": 9, "body": "x"})
    assert bad_mood.status_code == 422
    blank = await client.post(url, headers=h, json={"entry_date": today, "body": "   "})
    assert blank.status_code == 422
    future = (date.today() + timedelta(days=10)).isoformat()
    fut = await client.post(url, headers=h, json={"entry_date": future, "body": "x"})
    assert fut.status_code == 422


async def test_journal_is_private_to_owner(client, unique_email):
    a = await register_and_login(client, unique_email)
    b = await register_and_login(client, "other-" + unique_email)
    created = await client.post(
        "/api/v1/journal",
        headers=_h(a["access_token"]),
        json={"entry_date": date.today().isoformat(), "body": "private"},
    )
    entry_id = created.json()["id"]
    hb = _h(b["access_token"])
    assert (await client.get(f"/api/v1/journal/{entry_id}", headers=hb)).status_code == 404
    assert (await client.delete(f"/api/v1/journal/{entry_id}", headers=hb)).status_code == 404
    assert (await client.get("/api/v1/journal", headers=hb)).json()["total"] == 0


async def test_journal_requires_authentication(client):
    assert (await client.get("/api/v1/journal")).status_code in (401, 403)
