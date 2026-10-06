"""
Document-intelligence tests: medical-image (X-ray) handling, honest OCR
statuses, AI extraction with hallucination grounding, plain-language
explanations, preview, reprocess and provenance of reviewed suggestions.

AI is always a fake provider here (no Ollama needed): the point is to prove
the SAFETY behaviour around whatever a model returns.
"""
import io
import json

import pytest

from app.ai.document_schemas import EXPLANATION_PREFIX, StructuredDocumentExtraction
from app.ai.interface import AIProvider, AISummaryRequest, AISummaryResult
from app.core.config import settings
from app.ocr.null_engine import NullOCREngine
from app.services.document_ai_service import ground_extraction
from tests.conftest import register_and_login

pytestmark = pytest.mark.asyncio


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _pdf(text: str) -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in text.splitlines():
        page.insert_text((72, y), line)
        y += 16
    out = doc.tobytes()
    doc.close()
    return out


def _png(color: str = "black", size=(64, 64)) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format="PNG")
    return buf.getvalue()


REPORT_TEXT = (
    "City Hospital Laboratory Report\n"
    "Patient visit summary 2026-03-14\n"
    "Metformin 500mg twice daily\n"
    "Diagnosis: Type 2 Diabetes\n"
    "Hemoglobin 13.2 g/dL\n"
    "Cholesterol 232 mg/dL\n"
    "Recommend follow up in 3 months"
)


class FakeAI(AIProvider):
    """Returns canned JSON. `extraction` / `explanation` are what the
    'model' says; tests make them partly hallucinated on purpose."""

    model = "fake-llm"
    vision_model = "fake-vision"

    def __init__(self, extraction=None, explanation=None, image=None):
        self.extraction = extraction
        self.explanation = explanation
        self.image = image
        self.calls = 0

    async def generate_summary(self, request: AISummaryRequest) -> AISummaryResult:
        raise NotImplementedError

    async def is_available(self) -> bool:
        return True

    async def generate_json(self, *, prompt, images=None, use_vision_model=False) -> str:
        self.calls += 1
        if use_vision_model:
            return json.dumps(self.image or {})
        if "explain this document" in prompt:
            return json.dumps(self.explanation or {})
        return json.dumps(self.extraction or {})


@pytest.fixture
def enable_ai(monkeypatch):
    def _enable(provider: AIProvider):
        monkeypatch.setattr(settings, "ai_enabled", True)
        monkeypatch.setattr(
            "app.services.document_processing_service.get_ai_provider", lambda: provider
        )
        monkeypatch.setattr("app.services.document_service.get_ai_provider", lambda: provider)
        return provider

    return _enable


async def _upload(client, headers, *, name, content, mime, category=None, title="Doc"):
    data = {"title": title}
    if category:
        data["category"] = category
    resp = await client.post(
        "/api/v1/documents", headers=headers, files={"file": (name, content, mime)}, data=data
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _doc(client, headers, doc_id):
    """The upload response is a snapshot taken before the background task
    runs; fetch the document again to see its processed state."""
    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _extraction(client, headers, doc_id):
    resp = await client.get(f"/api/v1/documents/{doc_id}/extraction", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


# --------------------------------------------------------------------------
# Heuristic extractor regression: lab rows are not medications
# --------------------------------------------------------------------------
async def test_lab_rows_are_not_suggested_as_medications(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="r.pdf", content=_pdf(REPORT_TEXT), mime="application/pdf",
        category="lab_report",
    )
    extracted = (await _extraction(client, headers, doc["id"]))["extracted_data"]
    names = [m["name"] for m in extracted["medications"]]
    assert names == ["Metformin"]


# --------------------------------------------------------------------------
# X-rays / medical images
# --------------------------------------------------------------------------
async def test_xray_image_is_stored_but_never_interpreted(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="chest.png", content=_png(), mime="image/png", category="xray"
    )

    after = await _doc(client, headers, doc["id"])
    assert after["ocr_status"] == "not_applicable"
    assert after["processing_status"] == "processed"

    extraction = await _extraction(client, headers, doc["id"])
    extracted = extraction["extracted_data"]
    assert extracted["document_kind"] == "medical_image"
    assert extracted["imaging"]["interpretation"] == "not_performed"
    assert "does not interpret" in extracted["imaging"]["notice"]
    assert extracted["medications"] == [] and extracted["conditions"] == []
    assert extracted["imaging"]["image_info"]["width"] == 64


async def test_xray_vision_description_is_descriptive_only(
    client, unique_email, enable_ai, monkeypatch
):
    monkeypatch.setattr(settings, "ai_vision_enabled", True)
    provider = enable_ai(
        FakeAI(
            image={
                "modality_guess": "xray",
                "body_region_guess": "chest",
                "image_quality": "good",
                "visible_text": ["R"],
                # A model trying to sneak in a finding: no such field exists
                # in the schema, so it is ignored/stripped.
                "findings": "fracture of the left rib",
            }
        )
    )
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="chest.png", content=_png(), mime="image/png", category="xray"
    )
    imaging = (await _extraction(client, headers, doc["id"]))["extracted_data"]["imaging"]

    assert provider.calls == 1
    assert imaging["ai_description"]["modality_guess"] == "xray"
    assert imaging["ai_description"]["body_region_guess"] == "chest"
    assert "findings" not in imaging["ai_description"]
    assert "fracture" not in json.dumps(imaging)


async def test_imaging_documents_refuse_explanations(client, unique_email, enable_ai):
    enable_ai(FakeAI())
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="ct.png", content=_png(), mime="image/png", category="ct_scan"
    )
    resp = await client.post(f"/api/v1/documents/{doc['id']}/explain", headers=headers)
    assert resp.status_code == 422
    assert "aren't interpreted" in resp.json()["error"]["message"]


async def test_image_without_ocr_is_reported_skipped_not_completed(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="scan.png", content=_png("white"), mime="image/png",
        category="lab_report",
    )
    assert (await _doc(client, headers, doc["id"]))["ocr_status"] == "skipped"
    extracted = (await _extraction(client, headers, doc["id"]))["extracted_data"]
    assert "switched off" in extracted["notice"]


async def test_image_with_no_readable_text_is_reported_no_text(
    client, unique_email, monkeypatch
):
    class EmptyOCR(NullOCREngine):
        is_real = True

    monkeypatch.setattr(
        "app.services.document_processing_service.get_ocr_engine", lambda: EmptyOCR()
    )
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="photo.png", content=_png("white"), mime="image/png",
        category="other",
    )
    assert (await _doc(client, headers, doc["id"]))["ocr_status"] == "no_text"
    extracted = (await _extraction(client, headers, doc["id"]))["extracted_data"]
    assert "No readable text" in extracted["notice"]


async def test_real_tesseract_reads_light_on_dark_annotations():
    """The X-ray annotation pass must read white-on-black burned-in text."""
    pytest.importorskip("pytesseract")
    from PIL import Image, ImageDraw, ImageFont

    from app.ocr.factory import _build_tesseract_engine

    engine = _build_tesseract_engine()
    if not engine.is_real:
        pytest.skip("tesseract binary not installed")

    image = Image.new("RGB", (900, 300), "black")
    ImageDraw.Draw(image).text(
        (30, 100), "RIGHT CHEST 14/03/2026", fill="white", font=ImageFont.load_default(size=56)
    )
    buf = io.BytesIO()
    image.save(buf, format="PNG")

    result = await engine.extract_annotations(file_bytes=buf.getvalue(), mime_type="image/png")
    assert "RIGHT" in result.raw_text.upper()
    assert "2026" in result.raw_text


# --------------------------------------------------------------------------
# AI extraction + hallucination grounding
# --------------------------------------------------------------------------
async def test_ground_extraction_drops_anything_not_in_the_document():
    extraction = StructuredDocumentExtraction.model_validate(
        {
            "medications": [
                {"name": "Metformin", "dosage": "500 mg", "frequency": "twice daily"},
                {"name": "Warfarin", "dosage": "5 mg"},  # not in text
                {"name": "Metformin", "dosage": "9000 mg"},  # dosage not in text
            ],
            "conditions": ["Type 2 Diabetes", "Cancer"],
            "lab_values": [
                {"label": "Hemoglobin", "value": "13.2", "unit": "g/dL"},
                {"label": "Hemoglobin", "value": "99"},  # wrong value
            ],
        }
    )
    grounded = ground_extraction(extraction, REPORT_TEXT)
    assert [m.name for m in grounded.medications] == ["Metformin", "Metformin"]
    assert grounded.medications[0].dosage == "500 mg"
    assert grounded.medications[1].dosage is None
    assert grounded.conditions == ["Type 2 Diabetes"]
    assert [lab.value for lab in grounded.lab_values] == ["13.2"]


async def test_ai_enrichment_adds_grounded_items_and_labels_them(
    client, unique_email, enable_ai
):
    provider = enable_ai(
        FakeAI(
            extraction={
                "document_type": "lab report",
                "medications": [
                    {"name": "Metformin", "dosage": "500mg", "frequency": "twice daily"},
                    {"name": "Warfarin", "dosage": "5 mg"},  # hallucinated
                ],
                "conditions": ["Type 2 Diabetes", "Hypertension"],  # 2nd hallucinated
                "procedures": ["follow up"],
            }
        )
    )
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="r.pdf",
        content=_pdf(REPORT_TEXT + "\nProcedure: follow up visit"),
        mime="application/pdf", category="lab_report",
    )
    extraction = await _extraction(client, headers, doc["id"])
    extracted = extraction["extracted_data"]

    assert provider.calls == 1
    assert extracted["extraction_method"] == "pattern+ai"
    assert extracted["ai_status"] == "done"
    assert extracted["ai_model"] == "fake-llm"
    assert "Hypertension" not in extracted["conditions"]
    assert all(m["name"] != "Warfarin" for m in extracted["medications"])
    assert "follow up" in extracted["procedures"]
    assert extracted["ai_added"]["procedures"] == ["follow up"]
    # Still a suggestion awaiting the patient's review.
    assert extraction["status"] == "pending_review"


async def test_ai_failure_keeps_pattern_results(client, unique_email, enable_ai):
    class Broken(FakeAI):
        async def generate_json(self, **kwargs):
            return "this is not json at all"

    enable_ai(Broken())
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="r.pdf", content=_pdf(REPORT_TEXT), mime="application/pdf",
        category="lab_report",
    )
    assert (await _doc(client, headers, doc["id"]))["processing_status"] == "processed"
    extracted = (await _extraction(client, headers, doc["id"]))["extracted_data"]
    assert extracted["ai_status"] == "failed"
    assert extracted["medications"][0]["name"] == "Metformin"


# --------------------------------------------------------------------------
# Explanations
# --------------------------------------------------------------------------
GOOD_EXPLANATION = {
    "explanation": EXPLANATION_PREFIX + " It is a lab report listing a hemoglobin value.",
    "terms": [{"term": "Hemoglobin", "meaning": "A protein in red blood cells."}],
    "questions_for_doctor": ["What does this result mean for me?"],
}


async def test_explain_returns_validated_plain_language(client, unique_email, enable_ai):
    enable_ai(FakeAI(explanation=GOOD_EXPLANATION))
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="r.pdf", content=_pdf(REPORT_TEXT), mime="application/pdf",
        category="lab_report",
    )
    resp = await client.post(f"/api/v1/documents/{doc['id']}/explain", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["explanation"].startswith(EXPLANATION_PREFIX)
    assert body["terms"][0]["term"] == "Hemoglobin"
    assert body["model"] == "fake-llm"

    # Stored with the extraction so it is not regenerated on every view.
    stored = (await _extraction(client, headers, doc["id"]))["extracted_data"]["explanation"]
    assert stored["explanation"] == body["explanation"]


async def test_explain_without_safety_prefix_is_rejected(client, unique_email, enable_ai):
    enable_ai(FakeAI(explanation={**GOOD_EXPLANATION, "explanation": "You have diabetes."}))
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="r.pdf", content=_pdf(REPORT_TEXT), mime="application/pdf",
        category="lab_report",
    )
    resp = await client.post(f"/api/v1/documents/{doc['id']}/explain", headers=headers)
    assert resp.status_code == 502
    stored = (await _extraction(client, headers, doc["id"]))["extracted_data"]
    assert "explanation" not in stored


async def test_explain_disabled_or_other_users_document(client, unique_email, enable_ai):
    provider = enable_ai(FakeAI(explanation=GOOD_EXPLANATION))
    owner = await register_and_login(client, unique_email)
    owner_h = _auth(owner["access_token"])
    doc = await _upload(
        client, owner_h, name="r.pdf", content=_pdf(REPORT_TEXT), mime="application/pdf",
        category="lab_report",
    )
    intruder = await register_and_login(client, "intruder-" + unique_email)
    resp = await client.post(
        f"/api/v1/documents/{doc['id']}/explain", headers=_auth(intruder["access_token"])
    )
    assert resp.status_code == 404
    assert provider.calls <= 1  # only the owner's upload-time extraction call


async def test_explain_respects_data_sharing_consent_off(client, unique_email, enable_ai):
    enable_ai(FakeAI(explanation=GOOD_EXPLANATION))
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="r.pdf", content=_pdf(REPORT_TEXT), mime="application/pdf",
        category="lab_report",
    )
    put = await client.put(
        "/api/v1/preferences", headers=headers, json={"data_sharing_consent": False}
    )
    assert put.status_code == 200, put.text
    resp = await client.post(f"/api/v1/documents/{doc['id']}/explain", headers=headers)
    assert resp.status_code == 422


# --------------------------------------------------------------------------
# Preview / reprocess
# --------------------------------------------------------------------------
async def test_preview_is_inline_and_owner_only(client, unique_email):
    owner = await register_and_login(client, unique_email)
    owner_h = _auth(owner["access_token"])
    png = _png()
    doc = await _upload(client, owner_h, name="x.png", content=png, mime="image/png",
                        category="xray")
    resp = await client.get(f"/api/v1/documents/{doc['id']}/preview", headers=owner_h)
    assert resp.status_code == 200
    assert resp.content == png
    assert resp.headers["content-disposition"].startswith("inline")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert "sandbox" in resp.headers["content-security-policy"]

    intruder = await register_and_login(client, "i-" + unique_email)
    other = await client.get(
        f"/api/v1/documents/{doc['id']}/preview", headers=_auth(intruder["access_token"])
    )
    assert other.status_code == 404


async def test_reprocess_reruns_pipeline_and_is_owner_only(client, unique_email, monkeypatch):
    owner = await register_and_login(client, unique_email)
    owner_h = _auth(owner["access_token"])
    doc = await _upload(
        client, owner_h, name="r.png", content=_png("white"), mime="image/png",
        category="lab_report",
    )
    assert (await _doc(client, owner_h, doc["id"]))["ocr_status"] == "skipped"

    class FakeOCR(NullOCREngine):
        is_real = True

        async def extract(self, *, file_bytes, mime_type):
            from app.ocr.interface import OCRResult

            return OCRResult(raw_text=REPORT_TEXT, confidence=0.9, engine="fake")

    monkeypatch.setattr(
        "app.services.document_processing_service.get_ocr_engine", lambda: FakeOCR()
    )
    resp = await client.post(f"/api/v1/documents/{doc['id']}/reprocess", headers=owner_h)
    assert resp.status_code == 202, resp.text
    after = await client.get(f"/api/v1/documents/{doc['id']}", headers=owner_h)
    assert after.json()["ocr_status"] == "completed"
    extracted = (await _extraction(client, owner_h, doc["id"]))["extracted_data"]
    assert extracted["medications"][0]["name"] == "Metformin"

    intruder = await register_and_login(client, "i-" + unique_email)
    other = await client.post(
        f"/api/v1/documents/{doc['id']}/reprocess", headers=_auth(intruder["access_token"])
    )
    assert other.status_code == 404


# --------------------------------------------------------------------------
# Provenance: patient confirms a suggestion -> record remembers its source
# --------------------------------------------------------------------------
async def test_record_created_from_reviewed_suggestion_keeps_source(client, unique_email):
    data = await register_and_login(client, unique_email)
    headers = _auth(data["access_token"])
    doc = await _upload(
        client, headers, name="r.pdf", content=_pdf(REPORT_TEXT), mime="application/pdf",
        category="lab_report",
    )
    for path, payload in [
        ("medications", {"name": "Metformin", "dosage": "500 mg"}),
        ("allergies", {"name": "Penicillin"}),
        ("conditions", {"name": "Type 2 Diabetes"}),
    ]:
        resp = await client.post(
            f"/api/v1/{path}", headers=headers, json={**payload, "source_document_id": doc["id"]}
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["source"] == "document_extraction"
        assert resp.json()["source_document_id"] == doc["id"]

    manual = await client.post("/api/v1/allergies", headers=headers, json={"name": "Latex"})
    assert manual.json()["source"] == "manual"
    assert manual.json()["source_document_id"] is None


async def test_cannot_link_record_to_someone_elses_document(client, unique_email):
    owner = await register_and_login(client, unique_email)
    doc = await _upload(
        client, _auth(owner["access_token"]), name="r.pdf", content=_pdf(REPORT_TEXT),
        mime="application/pdf", category="lab_report",
    )
    intruder = await register_and_login(client, "i-" + unique_email)
    resp = await client.post(
        "/api/v1/medications",
        headers=_auth(intruder["access_token"]),
        json={"name": "Metformin", "source_document_id": doc["id"]},
    )
    assert resp.status_code == 404
