"""
Part G security-audit tests: probes that specifically try to break the
things the audit checklist calls out (file upload path traversal, SQL
injection via string formatting, CORS wildcard-with-credentials, error
leakage). Most individual protections already have dedicated tests
elsewhere (magic-byte / extension / size checks in test_documents.py,
refresh-token rotation in test_auth.py, IDOR sweeps throughout); this file
covers what wasn't already exercised.
"""
import re
from pathlib import Path

import pytest

from app.core.config import settings
from app.storage.local_storage import LocalStorageBackend
from tests.conftest import register_and_login

_APP_DIR = Path(__file__).resolve().parent.parent / "app"


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# -- file upload: path traversal ------------------------------------------------


@pytest.mark.asyncio
async def test_upload_with_path_traversal_filename_is_neutralized(client, unique_email):
    """A filename like '../../etc/passwd.pdf' must never let the stored
    file escape the storage directory, and the original filename returned
    to the client must be sanitized (no directory components)."""
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "Suspicious upload"},
        files={
            "file": ("../../../etc/passwd.pdf", b"%PDF-1.4 fake pdf content", "application/pdf")
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert ".." not in body["original_filename"]
    assert "/" not in body["original_filename"]

    # The file is retrievable normally, proving it was written under the
    # storage root rather than at the traversed path.
    download_resp = await client.get(
        f"/api/v1/documents/{body['id']}/download", headers=headers
    )
    assert download_resp.status_code == 200
    assert download_resp.content == b"%PDF-1.4 fake pdf content"


@pytest.mark.asyncio
async def test_local_storage_backend_rejects_traversal_paths(tmp_path):
    backend = LocalStorageBackend(base_path=str(tmp_path))
    with pytest.raises(ValueError):
        await backend.read(storage_path="../../etc/passwd")
    with pytest.raises(ValueError):
        await backend.save(relative_path="../escape.txt", content=b"x")


@pytest.mark.asyncio
async def test_upload_oversized_file_is_rejected_even_with_correct_type(
    client, unique_email, monkeypatch
):
    """Re-verifies the size check is enforced independent of a valid magic
    byte / extension match (see also test_documents.py's dedicated test)."""
    monkeypatch.setattr(settings, "max_upload_size_mb", 0)  # anything is "oversized"
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "Too big"},
        files={"file": ("report.pdf", b"%PDF-1.4 " + b"x" * 1000, "application/pdf")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_rejects_exe_content_renamed_as_pdf(client, unique_email):
    """A Windows PE executable's magic bytes ('MZ...') renamed with a .pdf
    extension must be rejected by the magic-byte check."""
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        data={"title": "Not actually a PDF"},
        files={
            "file": (
                "malware.pdf",
                b"MZ\x90\x00\x03\x00\x00\x00random binary junk",
                "application/pdf",
            )
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


# -- CORS -------------------------------------------------------------------------


def test_cors_never_wildcards_with_credentials():
    from app.main import app

    cors_middleware = next(
        m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"
    )
    kwargs = cors_middleware.kwargs
    assert kwargs["allow_credentials"] is True
    assert "*" not in kwargs["allow_origins"]
    assert kwargs["allow_origins"] == settings.cors_origins_list


# -- error leakage ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_unexpected_exception_never_leaks_internal_detail(
    client, unique_email, monkeypatch
):
    from app.repositories import medication_repository

    async def _boom(self, patient_id, **kwargs):
        raise RuntimeError("super secret internal detail: db connection string leaked")

    monkeypatch.setattr(medication_repository.MedicationRepository, "list_for_patient", _boom)

    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.get("/api/v1/medications", headers=headers)

    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "internal_error"
    assert "super secret" not in resp.text
    assert "RuntimeError" not in resp.text
    assert "Traceback" not in resp.text


# -- SQL injection: static sweep for raw string-formatted SQL --------------------


def test_no_raw_string_formatted_sql_in_repositories():
    """Every repository must build queries with the SQLAlchemy Core/ORM
    query builder (parameterized), never f-string/.format()-interpolated
    raw SQL. A `text(...)` call with pre-formatted content, or an f-string
    containing a SQL keyword, is exactly the pattern that enables SQL
    injection."""
    repo_dir = _APP_DIR / "repositories"
    offending: list[str] = []
    sql_keyword_pattern = re.compile(r"select|insert|update|delete|drop|union", re.IGNORECASE)

    for path in repo_dir.glob("*.py"):
        content = path.read_text()
        for lineno, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # f-strings that build something SQL-keyword-shaped.
            has_fstring = re.search(r'f"[^"]*"', line) or re.search(r"f'[^']*'", line)
            if has_fstring and sql_keyword_pattern.search(line):
                offending.append(f"{path.name}:{lineno}: {stripped}")
            if ".format(" in line and sql_keyword_pattern.search(line):
                offending.append(f"{path.name}:{lineno}: {stripped}")
            if re.search(r"text\(\s*f[\"']", line):
                offending.append(f"{path.name}:{lineno}: {stripped}")

    assert offending == [], f"Possible raw-SQL string formatting found: {offending}"


def test_health_ready_check_uses_parameterized_text_query():
    """The one legitimate `text(...)` call in the app (the readiness probe)
    is a fixed literal, never interpolated with a variable."""
    content = (_APP_DIR / "api" / "v1" / "health.py").read_text()
    assert 'text("SELECT 1")' in content


# -- secrets: nothing hardcoded in the code this checkpoint added ----------------


@pytest.mark.parametrize(
    "module_path",
    [
        "services/health_report_service.py",
        "services/notification_service.py",
        "services/audit_service.py",
        "services/preference_service.py",
        "pdf/reportlab_generator.py",
        "email/templates.py",
    ],
)
def test_new_modules_read_config_from_settings_not_hardcoded(module_path):
    content = (_APP_DIR / module_path).read_text()
    # No obvious hardcoded secret-shaped strings (API keys, connection
    # strings with embedded credentials).
    assert "postgresql://" not in content
    assert "sk-" not in content
    assert re.search(r'password\s*=\s*["\']', content) is None
