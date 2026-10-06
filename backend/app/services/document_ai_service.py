"""
AI-assisted document understanding. This is where an LLM earns its place in
the product: turning messy OCR text from lab reports, prescriptions and
discharge summaries into clean structured SUGGESTIONS, and explaining the
document's wording in plain language.

Safety design (all of it mechanical, none of it "trust the model"):

 1. The regex extractor always runs first and is the fallback - AI off,
    unreachable, slow or wrong never loses or blocks anything.
 2. Model output must parse through `StructuredDocumentExtraction`.
 3. GROUNDING: every item the model returns must literally appear in the
    document text (names, lab labels and values, dates). Anything that
    doesn't is dropped. This is the hallucination filter.
 4. Items the AI added are labelled (`source: "ai"` / `ai_added`) so the UI
    can show provenance, and the extraction stays `pending_review`; nothing
    reaches Medications/Allergies/Conditions without the patient adding it.
 5. Explanations must start with a fixed disclaimer and the schema offers no
    place for diagnoses or treatment advice.
"""
from __future__ import annotations

import re

from pydantic import ValidationError

from app.ai.document_prompts import build_explanation_prompt, build_extraction_prompt
from app.ai.document_schemas import DocumentExplanation, StructuredDocumentExtraction
from app.ai.interface import AIProvider
from app.ai.json_utils import extract_json_object
from app.core.config import settings
from app.core.exceptions import AIGenerationError
from app.core.logging import logger

_LIST_FIELDS = ("conditions", "allergies", "procedures", "dates", "recommendations")


def _norm(text: str) -> str:
    """Lower-cases and normalises whitespace so "500 mg" and "500mg" (or a
    line-wrapped phrase) compare equal when checking a value against the
    source text."""
    collapsed = re.sub(r"\s+", " ", text.lower().replace(",", ".")).strip()
    return re.sub(r"(\d) (?=[a-z%µμ])", r"\1", collapsed)


def _grounded(value: str | None, haystack: str) -> bool:
    return bool(value) and _norm(value) in haystack  # type: ignore[arg-type]


def ground_extraction(
    extraction: StructuredDocumentExtraction, document_text: str
) -> StructuredDocumentExtraction:
    """Keeps only what is literally present in `document_text`."""
    haystack = _norm(document_text)

    meds = []
    for med in extraction.medications:
        if not _grounded(med.name, haystack):
            continue
        meds.append(
            med.model_copy(
                update={
                    "dosage": med.dosage if _grounded(med.dosage, haystack) else None,
                    # Frequencies are often normalised ("BID" -> "twice daily"),
                    # so they are not required to match verbatim.
                }
            )
        )

    labs = [
        lab
        for lab in extraction.lab_values
        if _grounded(lab.label, haystack) and _grounded(lab.value, haystack)
    ]

    cleaned_lists = {
        field: [v for v in getattr(extraction, field) if _grounded(v, haystack)]
        for field in _LIST_FIELDS
    }
    return extraction.model_copy(update={"medications": meds, "lab_values": labs, **cleaned_lists})


def merge_ai_into_extracted(extracted: dict, ai: StructuredDocumentExtraction) -> dict:
    """Adds AI-found items that the heuristic pass missed. Existing items are
    never altered or removed (the patient's view stays stable); new items are
    labelled so the UI can show where they came from."""
    merged = {k: (list(v) if isinstance(v, list) else v) for k, v in extracted.items()}
    ai_added: dict[str, list] = {}

    known_meds = {m.get("name", "").lower() for m in merged.get("medications", [])}
    for med in ai.medications:
        if med.name.lower() in known_meds:
            continue
        known_meds.add(med.name.lower())
        entry = {"name": med.name, "dosage": med.dosage, "frequency": med.frequency, "source": "ai"}
        merged.setdefault("medications", []).append(entry)
        ai_added.setdefault("medications", []).append(med.name)

    known_lab_labels = {
        str(lv.get("label", "")).lower() for lv in merged.get("lab_values", [])
    }
    for lab in ai.lab_values:
        if lab.label.lower() in known_lab_labels:
            continue
        known_lab_labels.add(lab.label.lower())
        entry = {k: v for k, v in lab.model_dump().items() if v is not None}
        entry["source"] = "ai"
        merged.setdefault("lab_values", []).append(entry)
        ai_added.setdefault("lab_values", []).append(lab.label)

    for field in _LIST_FIELDS:
        existing = merged.setdefault(field, [])
        seen = {str(v).lower() for v in existing}
        for value in getattr(ai, field):
            if value.lower() not in seen:
                seen.add(value.lower())
                existing.append(value)
                ai_added.setdefault(field, []).append(value)

    if ai.document_type:
        merged["document_type_guess"] = ai.document_type
    merged["ai_added"] = ai_added
    return merged


async def extract_with_ai(
    *, provider: AIProvider, document_text: str
) -> StructuredDocumentExtraction | None:
    """One validated, grounded extraction attempt. Returns None on any
    failure (callers keep the heuristic result)."""
    if not document_text.strip():
        return None
    try:
        raw = await provider.generate_json(prompt=build_extraction_prompt(document_text))
        payload = extract_json_object(raw)
        if payload is None:
            return None
        extraction = StructuredDocumentExtraction.model_validate(payload)
    except (ValidationError, AIGenerationError, RuntimeError, NotImplementedError) as exc:
        logger.warning("AI document extraction unavailable: %s", type(exc).__name__)
        return None
    return ground_extraction(extraction, document_text)


async def explain_with_ai(
    *, provider: AIProvider, document_text: str, model_name: str
) -> dict:
    """Plain-language explanation. Raises `AIGenerationError` so the API can
    tell the patient clearly that it didn't work (unlike extraction, there is
    no silent fallback for an explicit user action)."""
    if not document_text.strip():
        raise AIGenerationError("This document has no readable text to explain.")

    for attempt in range(2):
        try:
            raw = await provider.generate_json(prompt=build_explanation_prompt(document_text))
        except AIGenerationError:
            raise
        except Exception as exc:
            logger.exception("AI explanation call failed.")
            raise AIGenerationError("The AI service failed. Please try again later.") from exc

        payload = extract_json_object(raw)
        if payload is not None:
            try:
                explanation = DocumentExplanation.model_validate(payload)
            except ValidationError:
                pass
            else:
                return {**explanation.model_dump(), "model": model_name}
        logger.warning("AI explanation failed validation (attempt %d).", attempt + 1)

    raise AIGenerationError(
        "The AI service didn't return a usable explanation. Please try again."
    )


def document_ai_enabled() -> bool:
    return settings.ai_enabled and settings.ai_document_extraction_enabled
