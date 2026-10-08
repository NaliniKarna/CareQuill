"""Password strength, sign-up consent and the public Contact Us form."""
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.password_policy import WeakPasswordError, validate_password_strength
from app.db.session import AsyncSessionLocal
from app.email.interface import EmailMessage, EmailSender, EmailSendResult
from app.models.user import User
from app.services import contact_service
from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio

WEAK = [
    "12345678",
    "password",
    "Password1!",  # common word
    "qwertyuiop",
    "Abcdefgh1!",  # alphabet run
    "aaaaaaaaaaA1!",
    "short1A!",  # too short
    "alllowercase#1",  # no uppercase
    "ALLUPPERCASE#1",  # no lowercase
    "NoNumbersHere#",  # no digit
    "NoSymbolsHere12",  # no symbol
    "CareQuill#2026",  # product name
]
STRONG = ["Mango-River-47!", "t7#Rk9!vLq2x", "Correct#Horse9Staple"]


@pytest.mark.parametrize("password", WEAK)
def test_weak_passwords_are_rejected(password):
    with pytest.raises(WeakPasswordError):
        validate_password_strength(password)


@pytest.mark.parametrize("password", STRONG)
def test_strong_passwords_are_accepted(password):
    assert validate_password_strength(password) == password


def test_password_containing_the_email_name_is_rejected():
    with pytest.raises(WeakPasswordError):
        validate_password_strength("Nalinikarna#2027", email="nalinikarna@example.com")


@pytest.mark.parametrize("password", ["12345678", "password123", "Qwerty123!"])
async def test_register_rejects_weak_password_with_a_helpful_message(
    client, unique_email, password
):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": unique_email, "password": password, "accepted_terms": True},
    )
    assert resp.status_code == 422
    assert "password" in str(resp.json()).lower()


async def test_register_requires_consent(client, unique_email):
    base = {"email": unique_email, "password": "Mango-River-47!"}
    missing = await client.post("/api/v1/auth/register", json=base)
    assert missing.status_code == 422
    refused = await client.post("/api/v1/auth/register", json={**base, "accepted_terms": False})
    assert refused.status_code == 422
    async with AsyncSessionLocal() as session:
        assert (await session.execute(select(User))).scalars().all() == []


async def test_consent_is_recorded_with_version_and_time(client, unique_email):
    await register_and_login(client, unique_email, password="Mango-River-47!")
    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User))).scalars().one()
    assert user.terms_accepted_at is not None
    assert user.terms_version == settings.terms_version


async def test_change_and_reset_password_enforce_the_policy(client, unique_email):
    data = await register_and_login(client, unique_email, password="Mango-River-47!")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    weak = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "Mango-River-47!", "new_password": "12345678"},
    )
    assert weak.status_code == 422
    ok = await client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "Mango-River-47!", "new_password": "t7#Rk9!vLq2x"},
    )
    assert ok.status_code in (200, 204)
    reset = await client.post(
        "/api/v1/auth/reset-password", json={"token": "x" * 30, "new_password": "password"}
    )
    assert reset.status_code == 422


async def test_existing_weak_password_can_still_log_in(client, unique_email):
    """Only NEW passwords are checked; nobody is locked out by the policy."""
    from app.core.security import hash_password
    from app.repositories.user_repository import UserRepository

    async with AsyncSessionLocal() as session:
        await UserRepository(session).create(
            email=unique_email, password_hash=hash_password("12345678")
        )
        await session.commit()
    resp = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "12345678"}
    )
    assert resp.status_code == 200


# -- contact form ---------------------------------------------------------------
class _Capture(EmailSender):
    def __init__(self, succeed: bool = True) -> None:
        self.sent: list[EmailMessage] = []
        self.succeed = succeed

    async def send(self, message: EmailMessage) -> EmailSendResult:
        self.sent.append(message)
        return EmailSendResult(success=self.succeed, error_message=None if self.succeed else "x")


def _use(monkeypatch, sender: EmailSender) -> None:
    monkeypatch.setattr(contact_service, "get_email_sender", lambda: sender)


FORM = {"name": "Sita Sharma", "email": "sita@example.com", "message": "Hello, I have a question."}


async def test_contact_form_emails_the_team_with_reply_to(client, monkeypatch):
    sender = _Capture()
    _use(monkeypatch, sender)
    resp = await client.post("/api/v1/public/contact", json=FORM)
    assert resp.status_code == 200
    message = sender.sent[0]
    assert message.to == "supportcarequill@gmail.com"
    assert message.reply_to == "sita@example.com"
    assert "Hello, I have a question." in message.text_body


async def test_contact_form_escapes_html_and_blocks_header_injection(client, monkeypatch):
    sender = _Capture()
    _use(monkeypatch, sender)
    resp = await client.post(
        "/api/v1/public/contact",
        json={
            "name": "Eve\nBcc: attacker@example.com",
            "email": "eve@example.com",
            "message": "<script>alert(1)</script> long enough",
        },
    )
    assert resp.status_code == 200
    message = sender.sent[0]
    assert "\n" not in message.subject and "\r" not in message.subject
    assert "<script>" not in message.html_body
    assert "&lt;script&gt;" in message.html_body


async def test_contact_form_validates_and_traps_bots(client, monkeypatch):
    sender = _Capture()
    _use(monkeypatch, sender)
    short = await client.post("/api/v1/public/contact", json={**FORM, "message": "hi"})
    assert short.status_code == 422
    bad_email = await client.post("/api/v1/public/contact", json={**FORM, "email": "nope"})
    assert bad_email.status_code == 422
    bot = await client.post("/api/v1/public/contact", json={**FORM, "website": "http://spam"})
    assert bot.status_code == 200
    assert sender.sent == []


async def test_contact_form_reports_delivery_failure(client, monkeypatch):
    _use(monkeypatch, _Capture(succeed=False))
    resp = await client.post("/api/v1/public/contact", json=FORM)
    assert resp.status_code == 502
    assert "email us directly" in resp.json()["error"]["message"]


async def test_contact_form_is_rate_limited(client, monkeypatch):
    from app.core.rate_limit import reset_rate_limits

    _use(monkeypatch, _Capture())
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "contact_rate_limit_attempts", 2)
    reset_rate_limits()
    codes = [(await client.post("/api/v1/public/contact", json=FORM)).status_code for _ in range(3)]
    reset_rate_limits()
    assert codes == [200, 200, 429]
