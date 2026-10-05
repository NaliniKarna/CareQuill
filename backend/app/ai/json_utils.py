"""
Defensive JSON parsing for LLM output.

Providers are instructed to reply with a single JSON object, but a raw
text-completion API (Ollama's `/api/generate` in particular) can still wrap
it in a markdown code fence or add stray whitespace/prose around it despite
those instructions. This module never *trusts* the result -- it only makes
a best-effort attempt to recover a `dict` for `StructuredAISummary` to
actually validate. If nothing parseable is found, callers get `None` and
must treat that as a failed generation (see `AISummaryService`), never a
fabricated fallback.
"""
from __future__ import annotations

import json
import re

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```\s*$", re.IGNORECASE | re.MULTILINE)


def extract_json_object(text: str | None) -> dict | None:
    if not text:
        return None

    cleaned = _CODE_FENCE_RE.sub("", text.strip()).strip()

    parsed = _try_load(cleaned)
    if parsed is not None:
        return parsed

    # Fall back to the outermost `{...}` span, in case the model added
    # stray prose before/after the JSON object despite instructions.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return _try_load(cleaned[start : end + 1])


def _try_load(text: str) -> dict | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
