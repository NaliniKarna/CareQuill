import io

import pytest

from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _build_test_pdf_bytes(text: str) -> bytes:
    """Builds a tiny real PDF with an actual extractable text layer, using
    the same PyMuPDF library the processing pipeline uses to read PDFs."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _build_test_png_bytes() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), color="white").save(buffer, format="PNG")
    return buffer.getvalue()


async def test_upload_pdf_runs_ocr_pipeline_and_extracts_entities(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])

    pdf_bytes = _build_test_pdf_bytes(
        "Patient visit summary\n"
        "Metformin 500mg twice daily\n"
        "Diagnosis: Type 2 Diabetes\n"
        "Hemoglobin: 13.5 g/dL\n"
        "Recommend follow up in 3 months"
    )

    upload_resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Lab Report", "category": "lab_report"},
    )
    assert upload_resp.status_code == 201, upload_resp.text
    body = upload_resp.json()
    assert body["title"] == "Lab Report"
    assert body["mime_type"] == "application/pdf"
    assert "storage_path" not in body
    assert "stored_filename" not in body
    document_id = body["id"]

    # The background OCR/extraction task has already run by the time the
    # ASGI request/response cycle completes.
    extraction_resp = await client.get(
        f"/api/v1/documents/{document_id}/extraction", headers=headers
    )
    assert extraction_resp.status_code == 200, extraction_resp.text
    extraction = extraction_resp.json()
    assert extraction["status"] == "pending_review"
    assert extraction["extracted_data"]["medications"][0]["name"] == "Metformin"
    assert "Type 2 Diabetes" in extraction["extracted_data"]["conditions"]
    assert extraction["extracted_data"]["lab_values"][0]["label"] == "Hemoglobin"
    assert any(
        "Recommend follow up" in rec for rec in extraction["extracted_data"]["recommendations"]
    )

    doc_resp = await client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert doc_resp.json()["ocr_status"] == "completed"
    assert doc_resp.json()["processing_status"] == "processed"


async def test_upload_png_document(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    png_bytes = _build_test_png_bytes()

    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("xray.png", png_bytes, "image/png")},
        data={"title": "X-Ray", "category": "xray"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["mime_type"] == "image/png"


async def test_documents_requires_authentication(client):
    resp = await client.get("/api/v1/documents")
    assert resp.status_code in (401, 403)


async def test_upload_rejects_disallowed_extension(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("malware.exe", b"not a real document", "application/octet-stream")},
        data={"title": "Suspicious"},
    )
    assert resp.status_code == 422


async def test_upload_rejects_spoofed_file_content(client, unique_email):
    """A file renamed to `.pdf` whose bytes are not actually a PDF must be
    rejected by the magic-byte check, not just the extension check."""
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("fake.pdf", b"this is just plain text, not a pdf", "application/pdf")},
        data={"title": "Spoofed"},
    )
    assert resp.status_code == 422


async def test_upload_rejects_oversized_file(client, unique_email, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "max_upload_size_mb", 0)

    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    pdf_bytes = _build_test_pdf_bytes("Some content")
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Too Big"},
    )
    assert resp.status_code == 422


async def test_upload_rejects_invalid_category(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    pdf_bytes = _build_test_pdf_bytes("Some content")
    resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Bad Category", "category": "not_a_real_category"},
    )
    assert resp.status_code == 422


async def test_list_documents_with_filters(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    pdf_bytes = _build_test_pdf_bytes("Content")

    await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("a.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Blood Panel", "category": "blood_test"},
    )
    await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("b.pdf", pdf_bytes, "application/pdf")},
        data={"title": "X-Ray Chest", "category": "xray"},
    )

    all_resp = await client.get("/api/v1/documents", headers=headers)
    assert all_resp.json()["total"] == 2

    category_resp = await client.get(
        "/api/v1/documents", headers=headers, params={"category": "xray"}
    )
    assert category_resp.json()["total"] == 1
    assert category_resp.json()["items"][0]["title"] == "X-Ray Chest"

    search_resp = await client.get(
        "/api/v1/documents", headers=headers, params={"q": "blood"}
    )
    assert search_resp.json()["total"] == 1


async def test_download_document_returns_original_bytes(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    pdf_bytes = _build_test_pdf_bytes("Downloadable content")

    upload_resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Report"},
    )
    document_id = upload_resp.json()["id"]

    download_resp = await client.get(
        f"/api/v1/documents/{document_id}/download", headers=headers
    )
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert download_resp.content == pdf_bytes


async def test_delete_document(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    pdf_bytes = _build_test_pdf_bytes("To be deleted")

    upload_resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Report"},
    )
    document_id = upload_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/documents/{document_id}", headers=headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_patch_extraction_status(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth_headers(data["access_token"])
    pdf_bytes = _build_test_pdf_bytes("Aspirin 100mg once daily")

    upload_resp = await client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Report"},
    )
    document_id = upload_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/documents/{document_id}/extraction",
        headers=headers,
        json={"status": "reviewed"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "reviewed"

    invalid_resp = await client.patch(
        f"/api/v1/documents/{document_id}/extraction",
        headers=headers,
        json={"status": "not_a_status"},
    )
    assert invalid_resp.status_code == 422


async def test_users_cannot_access_each_others_documents(client, unique_email):
    user_a = await register_and_login(client, unique_email)
    user_b = await register_and_login(client, f"b-{unique_email}")
    headers_a = _auth_headers(user_a["access_token"])
    headers_b = _auth_headers(user_b["access_token"])

    pdf_bytes = _build_test_pdf_bytes("Private medical content")
    upload_resp = await client.post(
        "/api/v1/documents",
        headers=headers_a,
        files={"file": ("private.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Private"},
    )
    document_id = upload_resp.json()["id"]

    assert (
        await client.get(f"/api/v1/documents/{document_id}", headers=headers_b)
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/documents/{document_id}/download", headers=headers_b)
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/documents/{document_id}/extraction", headers=headers_b)
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/documents/{document_id}/extraction",
            headers=headers_b,
            json={"status": "reviewed"},
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/documents/{document_id}", headers=headers_b)
    ).status_code == 404
    assert (await client.get("/api/v1/documents", headers=headers_b)).json()["total"] == 0
