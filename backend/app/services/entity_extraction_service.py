"""
Heuristic (regex/keyword based) structured medical entity extraction from
OCR'd document text. Deliberately *not* an LLM call -- this must work with
AI_ENABLED=false, since OCR/document processing is a separate concern from
the AI summary feature. Output is always a suggestion: it lands in
`document_extractions.extracted_data` and is never written into the
verified tables (allergies/medications/conditions) automatically.
"""
from __future__ import annotations

import re

# Small, curated keyword lists -- this is a heuristic aid, not a medical NLP
# model. Matching is case-insensitive and looks for the keyword as a whole
# word/phrase inside the cleaned text.
_KNOWN_CONDITIONS = {
    "diabetes": "Diabetes",
    "type 2 diabetes": "Type 2 Diabetes",
    "type 1 diabetes": "Type 1 Diabetes",
    "hypertension": "Hypertension",
    "high blood pressure": "Hypertension",
    "asthma": "Asthma",
    "hypothyroidism": "Hypothyroidism",
    "hyperthyroidism": "Hyperthyroidism",
    "anemia": "Anemia",
    "arthritis": "Arthritis",
    "coronary artery disease": "Coronary Artery Disease",
}

_KNOWN_ALLERGIES = {
    "penicillin": "Penicillin",
    "sulfa": "Sulfa",
    "latex": "Latex",
    "aspirin": "Aspirin",
    "peanut": "Peanut",
    "peanuts": "Peanut",
    "shellfish": "Shellfish",
    "ibuprofen": "Ibuprofen",
    "iodine": "Iodine",
}

_RECOMMENDATION_PREFIXES = ("recommend", "advised", "advice", "follow up", "f/u", "f u")

# Metformin 500mg twice daily / Paracetamol 650 mg BID / Amoxicillin 250mg TID
_MEDICATION_RE = re.compile(
    r"\b(?P<name>[A-Z][a-zA-Z]{2,30})\s+"
    r"(?P<dosage>\d+(?:\.\d+)?\s?(?:mg|mcg|g|ml|iu))"
    r"(?:\s+(?P<frequency>(?:once|twice|three times|four times)\s+(?:a\s+)?daily"
    r"|once daily|od|bid|tid|qid|q\.?d\.?|prn"
    r"|\d+\s*times?\s*(?:a|per)\s*day))?",
    re.IGNORECASE,
)

# Hemoglobin: 13.5 g/dL / Blood Glucose: 110 mg/dL
_LAB_VALUE_RE = re.compile(
    r"\b(?P<label>[A-Z][A-Za-z ]{2,40}?)\s*[:\-]\s*"
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mg/dL|g/dL|mmol/L|%|mEq/L|IU/L|U/L|/uL|/µL|bpm|mmHg)",
)

# Tabular lab report rows, one result per line, columns separated by
# whitespace rather than a colon -- e.g. a scanned "Test | Result | Units |
# Reference Range | Flag" table OCR's as one line per row:
#   "Glucose (fasting)   112   mg/dL   70 - 99   HIGH"
#   "WBC   6.8   x 10(9)/L   4.0 - 11.0"
# The colon-based _LAB_VALUE_RE above never matches this layout (no ":" or
# "-" directly after the label), so this is a separate pattern rather than
# a tweak to it. Unit is matched against a known list (including the
# cell-count exponent notation used by WBC/RBC/Platelets rows) rather than
# "whatever the next word is", to avoid false-positive matches on ordinary
# report prose that happens to start a line with a number.
_LAB_TABLE_ROW_RE = re.compile(
    r"^(?P<label>[A-Za-z][A-Za-z0-9 ()/\-]{1,40}?)\s+"
    r"(?P<value>\d+(?:\.\d+)?)\s+"
    r"(?P<unit>mmhg|bpm|%|mg/dl|g/dl|mmol/l|meq/l|iu/l|u/l|/u?l|/µl|/μl|"
    r"[×x]\s?10[⁰¹²³⁴⁵⁶⁷⁸⁹\d(){}^]{0,4}\s?/\s?[µμu]?l)"
    r"(?:\s+(?P<range>[<>]\s?\d+(?:\.\d+)?|\d+(?:\.\d+)?\s?(?:[-–]|to)\s?\d+(?:\.\d+)?))?"
    r"(?:\s+(?P<flag>high|low|critical|abnormal|normal))?"
    r"\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# Common date formats: 2026-03-14, 14/03/2026, 14-03-2026, March 14, 2026
_DATE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
    re.compile(r"\b\d{1,2}-\d{1,2}-\d{4}\b"),
    re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},?\s+\d{4}\b"
    ),
]

_FREQUENCY_ALIASES = {
    "od": "once daily",
    "bid": "twice daily",
    "tid": "three times daily",
    "qid": "four times daily",
    "prn": "as needed",
}


def clean_text(raw_text: str) -> str:
    """Collapse whitespace and strip control characters from raw OCR/PDF
    text before extraction."""
    if not raw_text:
        return ""
    # Strip non-printable control characters (keep newlines/tabs -> spaces).
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw_text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_entities(cleaned_text: str) -> dict:
    """Returns a dict matching exactly the shape documented in the task
    spec: medications, conditions, allergies, procedures, dates, lab_values,
    recommendations."""
    text = cleaned_text or ""
    lower_text = text.lower()

    medications = _extract_medications(text)
    conditions = _extract_keyword_matches(lower_text, _KNOWN_CONDITIONS)
    allergies = _extract_keyword_matches(lower_text, _KNOWN_ALLERGIES)
    dates = _extract_dates(text)
    lab_values = _extract_lab_values(text)
    recommendations = _extract_recommendations(text)

    return {
        "medications": medications,
        "conditions": conditions,
        "allergies": allergies,
        "procedures": [],
        "dates": dates,
        "lab_values": lab_values,
        "recommendations": recommendations,
    }


def _extract_medications(text: str) -> list[dict]:
    results: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for match in _MEDICATION_RE.finditer(text):
        name = match.group("name").strip()
        dosage = match.group("dosage").strip()
        # Normalize "500mg" -> "500 mg" for a consistent display value.
        dosage = re.sub(r"(\d)\s?([a-zA-Z]+)$", r"\1 \2", dosage)
        frequency_raw = (match.group("frequency") or "").strip().lower()
        frequency = _FREQUENCY_ALIASES.get(frequency_raw, frequency_raw) or None
        key = (name.lower(), dosage.lower())
        if key in seen:
            continue
        seen.add(key)
        results.append({"name": name, "dosage": dosage, "frequency": frequency})
    return results


def _extract_keyword_matches(lower_text: str, keyword_map: dict[str, str]) -> list[str]:
    found: list[str] = []
    seen_labels: set[str] = set()
    matched_keywords: list[str] = []
    # Longest keywords first so "type 2 diabetes" wins over the bare
    # "diabetes" substring match for the same mention (and the shorter
    # keyword is then skipped entirely, since it's contained in the longer
    # one that already matched).
    for keyword in sorted(keyword_map, key=len, reverse=True):
        if any(keyword in already for already in matched_keywords):
            continue
        if re.search(rf"\b{re.escape(keyword)}\b", lower_text):
            matched_keywords.append(keyword)
            label = keyword_map[keyword]
            if label not in seen_labels:
                seen_labels.add(label)
                found.append(label)
    return found


def _extract_dates(text: str) -> list[str]:
    dates: list[str] = []
    seen: set[str] = set()
    for pattern in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(0)
            if value not in seen:
                seen.add(value)
                dates.append(value)
    return dates


def _extract_lab_values(text: str) -> list[dict]:
    results: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for match in _LAB_VALUE_RE.finditer(text):
        label = match.group("label").strip()
        # Skip lines whose "label" is really the start of a sentence -- keep
        # this heuristic simple by requiring at least one letter and no more
        # than 5 words.
        if not label or len(label.split()) > 5:
            continue
        key = (label.lower(), match.group("value"))
        if key in seen:
            continue
        seen.add(key)
        results.append(
            {
                "label": label,
                "value": match.group("value"),
                "unit": match.group("unit"),
            }
        )

    for match in _LAB_TABLE_ROW_RE.finditer(text):
        label = match.group("label").strip(" .:-")
        if not label or len(label.split()) > 6:
            continue
        key = (label.lower(), match.group("value"))
        if key in seen:
            continue
        seen.add(key)
        entry: dict = {
            "label": label,
            "value": match.group("value"),
            "unit": match.group("unit").strip(),
        }
        if match.group("range"):
            entry["range"] = match.group("range").strip()
        if match.group("flag"):
            entry["flag"] = match.group("flag").strip().upper()
        results.append(entry)

    return results


def _extract_recommendations(text: str) -> list[str]:
    """Whole sentences that mention a recommendation keyword anywhere in
    them, not only ones where the keyword is the first word -- narrative
    report text commonly reads "Mildly elevated ... Recommend repeat
    glucose ..." with the keyword mid-sentence. Sentences are split after
    collapsing newlines, since OCR/PDF text wraps a single sentence across
    multiple lines."""
    recommendations: list[str] = []
    seen: set[str] = set()
    flattened = re.sub(r"\s+", " ", text).strip()
    for sentence in re.split(r"(?<=[.!?])\s+", flattened):
        stripped = sentence.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if any(
            re.search(rf"\b{re.escape(prefix)}\b", lowered)
            for prefix in _RECOMMENDATION_PREFIXES
        ):
            if stripped not in seen:
                seen.add(stripped)
                recommendations.append(stripped)
    return recommendations