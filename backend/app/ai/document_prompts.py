"""
Prompt construction for the document-intelligence features. Like
`app.ai.prompt`, prompt text lives ONLY here so the safety framing can't
drift between call sites or providers.

Every prompt (a) states the no-diagnosis rule, (b) tells the model to use
only what is written in the supplied text, and (c) fixes the exact JSON
shape, which `app.ai.document_schemas` then enforces.
"""
from __future__ import annotations

import json

from app.ai.document_schemas import EXPLANATION_PREFIX

# Keeps the whole prompt inside the configured context window
# (settings.ollama_num_ctx) with room for the answer.
MAX_DOCUMENT_CHARS = 12_000

_COMMON_RULES = (
    "You are a careful medical-document reading assistant inside a patient's "
    "personal health record app. You are NOT a doctor.\n"
    "Strict rules, no exceptions:\n"
    "- Use ONLY information that is literally written in the document text below.\n"
    "- Do NOT diagnose, interpret results as a disease, prescribe, or suggest "
    "starting/stopping/changing any medication.\n"
    "- Do NOT add anything from your own medical knowledge that is not in the text.\n"
    "- If something is not in the text, leave it out (empty list / null)."
)


def _truncate(text: str) -> str:
    if len(text) <= MAX_DOCUMENT_CHARS:
        return text
    return text[:MAX_DOCUMENT_CHARS] + "\n[... document truncated ...]"


_EXTRACTION_SHAPE = {
    "document_type": "e.g. 'lab report', 'prescription', 'discharge summary' - or null",
    "medications": [
        {"name": "as written", "dosage": "as written or null", "frequency": "as written or null"}
    ],
    "conditions": ["conditions/diagnoses the DOCUMENT itself states"],
    "allergies": ["allergies the DOCUMENT itself states"],
    "procedures": ["procedures the document mentions"],
    "dates": ["dates exactly as written"],
    "lab_values": [
        {"label": "test name", "value": "number as written", "unit": "or null",
         "range": "reference range as written or null", "flag": "HIGH/LOW as written or null"}
    ],
    "recommendations": ["follow-up / advice sentences exactly as the document states them"],
}


def build_extraction_prompt(document_text: str) -> str:
    return "\n".join(
        [
            _COMMON_RULES,
            "",
            "Task: extract the structured items below from the document text. Copy "
            "names and numbers exactly as written. Ignore patient/doctor names and "
            "hospital letterhead. Do not list a medication that is only mentioned as "
            "something the patient does NOT take, and do not list an allergy from a "
            "sentence such as 'no known allergies'.",
            "",
            "=== DOCUMENT TEXT (from OCR; may contain recognition errors) ===",
            _truncate(document_text),
            "",
            "Respond with ONLY a single JSON object of exactly this shape:",
            json.dumps(_EXTRACTION_SHAPE, indent=2),
        ]
    )


def build_explanation_prompt(document_text: str) -> str:
    shape = {
        "explanation": f"MUST start with exactly: {EXPLANATION_PREFIX!r} then 2-5 plain sentences "
        "(reading level ~12 years) saying what kind of document this is and what it states.",
        "terms": [{"term": "a medical word or abbreviation from the text",
                   "meaning": "what that word generally means, in plain words"}],
        "questions_for_doctor": ["up to 5 neutral questions the patient could ask their doctor"],
    }
    return "\n".join(
        [
            _COMMON_RULES,
            "- When the document marks a value as high/low, you may say the DOCUMENT marks it "
            "that way; never say what it means for the patient's health.",
            "- Explain terminology only. Questions must be neutral (e.g. 'What does this "
            "result mean for me?'), never suggest a cause or a treatment.",
            "",
            "Task: explain this document to the patient in plain language.",
            "",
            "=== DOCUMENT TEXT ===",
            _truncate(document_text),
            "",
            "Respond with ONLY a single JSON object of exactly this shape:",
            json.dumps(shape, indent=2),
        ]
    )


def build_image_description_prompt() -> str:
    shape = {
        "modality_guess": (
            "one of: xray, mri, ct, ultrasound, photo, document_scan, other - or null"
        ),
        "body_region_guess": "e.g. 'chest', 'left hand', 'knee' - or null if unsure",
        "view_or_orientation": "e.g. 'frontal', 'lateral' - or null",
        "image_quality": "good | fair | poor | null",
        "visible_text": ["any text, letters or numbers printed in the image, exactly as seen"],
    }
    return "\n".join(
        [
            "You are labeling an uploaded image for a patient's personal records app. "
            "You are NOT a radiologist or doctor.",
            "Strict rules, no exceptions:",
            "- Describe ONLY what kind of image this is. Do NOT report findings, "
            "abnormalities, fractures, masses, 'normal'/'abnormal', impressions or "
            "diagnoses - there is no field for them and you must not mention any.",
            "- If you are unsure of any field, use null.",
            "",
            "Respond with ONLY a single JSON object of exactly this shape:",
            json.dumps(shape, indent=2),
        ]
    )
