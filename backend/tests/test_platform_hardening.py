"""Production-readiness behaviour: rate limiting, config guard, security
headers, compression policy, Ollama + HTTP email providers (faked
transports), and recovery of interrupted document processing."""
import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import ValidationError

from app.ai.ollama_provider import OllamaAIProvider
from app.core.config import Settings, settings
from app.core.exceptions import AIGenerationError
from app.core.rate_limit import reset_rate_limits
from app.email.http_providers import MailgunEmailSender, SendGridEmailSender
from app.email.interface import EmailMessage
from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------
# Rate limiting
# --------------------------------------------------------------------------
async def test_login_is_rate_limited_per_client(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "auth_rate_limit_attempts", 3)
    reset_rate_limits()

    statuses = []
    for _ in range(5):
        resp = await client.post(
            "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-pass-1"}
        )
        statuses.append(resp.status_code)
    reset_rate_limits()

    assert statuses[:3] == [401, 401, 401]
    assert statuses[3:] == [429, 429]


async def test_rate_limit_error_uses_standard_envelope(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "auth_rate_limit_attempts", 1)
    reset_rate_limits()
    body = {"email": "nobody@example.com", "password": "wrong-pass-1"}
    await client.post("/api/v1/auth/login", json=body)
    resp = await client.post("/api/v1/auth/login", json=body)
    reset_rate_limits()
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "rate_limited"
    assert resp.json()["error"]["details"]["retry_after_seconds"] >= 1


# --------------------------------------------------------------------------
# Auth: unknown email vs wrong password look identical
# --------------------------------------------------------------------------
async def test_login_failure_is_identical_for_unknown_and_known_email(client, unique_email):
    await register_and_login(client, unique_email)
    wrong = await client.post(
        "/api/v1/auth/login", json={"email": unique_email, "password": "not-the-password"}
    )
    unknown = await client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": "not-the-password"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


# --------------------------------------------------------------------------
# Production config guard
# --------------------------------------------------------------------------
def _prod(**overrides):
    base = dict(
        environment="production",
        jwt_secret_key="x" * 48,
        database_url="postgresql+asyncpg://app:Str0ngPw@db:5432/app",
        cors_origins="https://app.example.com",
        email_backend="smtp",
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)


async def test_production_accepts_a_proper_configuration():
    assert _prod().environment == "production"


@pytest.mark.parametrize(
    "override",
    [
        {"jwt_secret_key": "change-this-to-a-random-64-char-hex-secret-before-deploying"},
        {"jwt_secret_key": "short"},
        {"database_url": "postgresql+asyncpg://medqueue:medqueue_dev_pw@db/app"},
        {"cors_origins": "*"},
        {"email_backend": "console"},
    ],
)
async def test_production_refuses_insecure_defaults(override):
    with pytest.raises(ValidationError):
        _prod(**override)


# --------------------------------------------------------------------------
# HTTP hardening / performance headers
# --------------------------------------------------------------------------
async def test_api_responses_carry_security_headers_and_timing(client):
    resp = await client.get("/api/v1/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
    assert resp.headers["cache-control"] == "no-store"
    assert int(resp.headers["x-process-time-ms"]) >= 0


async def test_large_json_is_gzipped_but_file_downloads_are_not(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    for i in range(40):
        await client.post(
            "/api/v1/medications", headers=headers, json={"name": f"Medication number {i}"}
        )
    listing = await client.get(
        "/api/v1/medications", headers={**headers, "Accept-Encoding": "gzip"}
    )
    assert listing.headers.get("content-encoding") == "gzip"

    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (400, 400), "white").save(buf, format="PNG")
    upload = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("x.png", buf.getvalue(), "image/png")},
        data={"title": "Pic", "category": "xray"},
    )
    download = await client.get(
        f"/api/v1/documents/{upload.json()['id']}/download",
        headers={**headers, "Accept-Encoding": "gzip"},
    )
    assert download.status_code == 200
    assert "content-encoding" not in download.headers


# --------------------------------------------------------------------------
# Ollama provider (fake transport)
# --------------------------------------------------------------------------
def _ollama(handler, **kw) -> OllamaAIProvider:
    return OllamaAIProvider(
        base_url="http://ollama.test",
        model="llama3.2",
        transport=httpx.MockTransport(handler),
        **kw,
    )


async def test_ollama_status_reports_missing_model_with_the_fix():
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": "mistral:latest"}]})

    provider = _ollama(handler)
    assert await provider.is_available() is False
    status = await provider.status()
    assert status.model_ready is False
    assert "ollama pull llama3.2" in status.detail


async def test_ollama_available_when_model_pulled_with_tag():
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": "llama3.2:latest"}]})

    assert await _ollama(handler).is_available() is True


async def test_ollama_unreachable_status_explains_host_binding():
    def handler(request):
        raise httpx.ConnectError("refused")

    status = await _ollama(handler).status()
    assert status.available is False
    assert "OLLAMA_HOST=0.0.0.0" in status.detail


async def test_ollama_request_sets_context_window_and_keep_alive():
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"response": '{"ok": true}'})

    out = await _ollama(handler).generate_json(prompt="hello")
    assert out == '{"ok": true}'
    assert seen["options"]["num_ctx"] == settings.ollama_num_ctx
    assert seen["keep_alive"] == settings.ollama_keep_alive
    assert seen["format"] == "json"


async def test_ollama_vision_call_sends_images_to_the_vision_model():
    seen = {}

    def handler(request):
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"response": "{}"})

    await _ollama(handler, vision_model="llava").generate_json(
        prompt="p", images=[b"\x89PNG"], use_vision_model=True
    )
    assert seen["model"] == "llava"
    assert len(seen["images"]) == 1


@pytest.mark.parametrize(
    ("handler_exc", "expected"),
    [
        (httpx.ReadTimeout("slow"), "took too long"),
        (httpx.ConnectError("refused"), "isn't reachable"),
    ],
)
async def test_ollama_errors_become_friendly_ai_generation_errors(handler_exc, expected):
    def handler(request):
        raise handler_exc

    with pytest.raises(AIGenerationError) as exc:
        await _ollama(handler).generate_json(prompt="x")
    assert expected in exc.value.message


async def test_ollama_404_means_model_not_installed():
    def handler(request):
        return httpx.Response(404, json={"error": "model not found"})

    with pytest.raises(AIGenerationError) as exc:
        await _ollama(handler).generate_json(prompt="x")
    assert "isn't installed" in exc.value.message


# --------------------------------------------------------------------------
# SendGrid / Mailgun (fake transport)
# --------------------------------------------------------------------------
def _message() -> EmailMessage:
    return EmailMessage(
        to="dr@example.com",
        subject="Health summary",
        html_body="<p>hi</p>",
        text_body="hi",
        attachments=[("summary.pdf", b"%PDF-1.4 test", "application/pdf")],
    )


async def test_sendgrid_sends_attachment_and_reports_success(monkeypatch):
    monkeypatch.setattr(settings, "sendgrid_api_key", "SG.test")
    captured = {}

    def handler(request):
        captured["auth"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(202, headers={"x-message-id": "abc123"})

    sender = SendGridEmailSender(transport=httpx.MockTransport(handler))
    result = await sender.send(_message())
    assert result.success and result.provider_message_id == "abc123"
    assert captured["auth"] == "Bearer SG.test"
    assert captured["body"]["attachments"][0]["filename"] == "summary.pdf"
    assert captured["body"]["personalizations"][0]["to"][0]["email"] == "dr@example.com"


async def test_sendgrid_failure_is_reported_without_leaking_body(monkeypatch):
    monkeypatch.setattr(settings, "sendgrid_api_key", "SG.test")

    def handler(request):
        return httpx.Response(401, json={"errors": [{"message": "secret details"}]})

    result = await SendGridEmailSender(transport=httpx.MockTransport(handler)).send(_message())
    assert result.success is False
    assert "HTTP 401" in result.error_message
    assert "secret details" not in result.error_message


async def test_mailgun_sends_multipart_with_attachment(monkeypatch):
    monkeypatch.setattr(settings, "mailgun_api_key", "key-test")
    monkeypatch.setattr(settings, "mailgun_domain", "mg.example.com")
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["content_type"] = request.headers["content-type"]
        captured["has_attachment"] = b"summary.pdf" in request.content
        return httpx.Response(200, json={"id": "<mg-1@example.com>", "message": "Queued"})

    result = await MailgunEmailSender(transport=httpx.MockTransport(handler)).send(_message())
    assert result.success and result.provider_message_id == "<mg-1@example.com>"
    assert captured["url"] == "https://api.mailgun.net/v3/mg.example.com/messages"
    assert captured["content_type"].startswith("multipart/form-data")
    assert captured["has_attachment"]


async def test_http_email_providers_require_credentials(monkeypatch):
    monkeypatch.setattr(settings, "sendgrid_api_key", None)
    monkeypatch.setattr(settings, "mailgun_api_key", None)
    with pytest.raises(ValueError):
        SendGridEmailSender()
    with pytest.raises(ValueError):
        MailgunEmailSender()


# --------------------------------------------------------------------------
# Recovery of interrupted processing
# --------------------------------------------------------------------------
async def test_recover_stuck_documents_requeues_old_unprocessed_uploads(client, unique_email):
    import io

    from PIL import Image
    from sqlalchemy import update

    from app.db.session import AsyncSessionLocal
    from app.models.medical_document import MedicalDocument
    from app.services.document_processing_service import recover_stuck_documents

    data = await register_and_login(client, unique_email)
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    buf = io.BytesIO()
    Image.new("RGB", (50, 50), "white").save(buf, format="PNG")
    upload = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("a.png", buf.getvalue(), "image/png")},
        data={"title": "Stuck", "category": "xray"},
    )
    doc_id = upload.json()["id"]

    # Simulate a crash mid-processing 30 minutes ago.
    async with AsyncSessionLocal() as session:
        await session.execute(
            update(MedicalDocument)
            .where(MedicalDocument.id == doc_id)
            .values(
                processing_status="processing",
                ocr_status="processing",
                updated_at=datetime.now(UTC) - timedelta(minutes=30),
            )
        )
        await session.commit()

    assert await recover_stuck_documents() == 1
    import asyncio

    await asyncio.sleep(0.5)
    after = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert after.json()["processing_status"] == "processed"
