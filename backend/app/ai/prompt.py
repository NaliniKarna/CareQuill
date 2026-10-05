"""
Structured prompt construction + hallucination-control framing, shared by
every `AIProvider` implementation. Prompt text is built ONLY here (imported
by `app.ai.ollama_provider`, and by any future provider) so the safety
instructions and the required JSON output contract can never drift between
providers, and are never rebuilt ad hoc inside `app.services`.

The JSON shape asked for here matches `app.ai.schemas.StructuredAISummary`
exactly -- that Pydantic model is the actual hallucination-control gate
(nothing is persisted, reviewed, or shared unless a provider's output
validates against it); this prompt just gives the model its best chance of
producing something that does.
"""
from __future__ import annotations

import json

from app.ai.interface import AISummaryRequest

# Verbatim system instruction required by the product spec.
SYSTEM_INSTRUCTION = (
    "You are generating an organizational summary for a healthcare "
    "professional. Do not diagnose, prescribe, infer unsupported medical "
    "facts, or invent information. If information is unavailable, say "
    "that it is unavailable."
)

# Required literal prefix for the structured output's "summary" field --
# enforced again, mechanically, by `StructuredAISummary`'s validator, so a
# provider can never slip past this by omission. Makes it unmistakable to a
# reading doctor that this is an AI-assisted draft, never a clinician's
# note.
REQUIRED_SUMMARY_PREFIX = (
    "AI-assisted summary generated from information provided by the "
    "patient and uploaded records."
)

# Extends (never replaces) the original organize/summarize-only safety
# framing: forbidden content types are named explicitly, plus the
# AI-extracted-vs-verified distinction this task adds.
_SAFETY_RULES = (
    "You are a health-information organizing assistant. You summarize and "
    "organize information the patient has already entered and verified, "
    "plus any AI-extracted document context the patient explicitly chose "
    "to include below (which you must always label as AI-extracted / "
    "unverified in your output, never merge into verified data). You must "
    "NOT replace a doctor. Strict rules, no exceptions:\n"
    "- Do NOT diagnose any condition.\n"
    "- Do NOT prescribe, recommend, or suggest starting, stopping, or "
    "changing any medication or dosage.\n"
    "- Do NOT infer, assume, or invent any medical fact, condition, "
    "medication, allergy, or event that is not explicitly present in the "
    "data given to you.\n"
    "- Do NOT state or imply certainty about a diagnosis or prognosis.\n"
    "- Do NOT present AI-extracted (unverified) information as verified.\n"
    "- If information relevant to a requested field is unavailable, list "
    "it under \"unavailable\" instead of guessing.\n"
    "- Write in clear, plain language suitable for sharing with a doctor."
)

_OUTPUT_SCHEMA = {
    "summary": (
        "plain-language paragraph(s); MUST start with exactly: "
        f"{REQUIRED_SUMMARY_PREFIX!r}"
    ),
    "verified_conditions": ["..."],
    "verified_medications": ["Name dosage frequency", "..."],
    "verified_allergies": ["..."],
    "recent_events": ["..."],
    "patient_concerns": "...",
    "ai_extracted_notes": [
        "clearly-flagged items pulled from the AI-extracted document data "
        "below, if any were provided -- otherwise an empty list"
    ],
    "unavailable": ["things you were asked about but had no data for"],
}

_STRICT_JSON_INSTRUCTION = (
    "Your previous response could not be parsed as valid JSON matching the "
    "required shape below. This time, reply with ONLY valid JSON matching "
    "the required shape -- no prose, no markdown code fences, no "
    "explanation outside the single JSON object."
)


def build_prompt(request: AISummaryRequest) -> str:
    """Builds the full, provider-agnostic prompt text for one generation
    attempt. `request.strict_json_retry` controls whether the stricter
    "reply with ONLY JSON" instruction is included, for the one safe retry
    `AISummaryService` performs after a first response fails validation."""
    sections: list[str] = [SYSTEM_INSTRUCTION, "", _SAFETY_RULES, ""]

    if request.strict_json_retry:
        sections += [_STRICT_JSON_INSTRUCTION, ""]

    sections += [
        "=== VERIFIED PATIENT DATA (from the patient's current, "
        "patient-confirmed health snapshot -- treat as ground truth) ===",
        json.dumps(request.snapshot_data, indent=2, default=str),
        "",
        "=== RECENT HEALTH TIMELINE (most relevant entries only) ===",
        (
            json.dumps(request.timeline_entries, indent=2, default=str)
            if request.timeline_entries
            else "(none provided)"
        ),
        "",
        "=== PATIENT'S STATED CONCERNS FOR THIS VISIT (patient's own words) ===",
        request.patient_concerns or "(none provided)",
        "",
        "=== AI-EXTRACTED / UNVERIFIED DOCUMENT DATA (patient-selected; "
        "NEVER treat as verified -- always label it as AI-extracted in "
        "your output) ===",
        (
            json.dumps(request.document_extractions, indent=2, default=str)
            if request.document_extractions
            else "(none provided)"
        ),
        "",
        "Respond with ONLY a single JSON object matching exactly this "
        "shape (no extra keys, no prose outside the JSON):",
        json.dumps(_OUTPUT_SCHEMA, indent=2),
    ]
    return "\n".join(sections)
