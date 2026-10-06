# AI / OCR pipeline

MedQueue AI is an **organizational and communication assistant**. It does
not diagnose conditions, prescribe treatment, or act as an autonomous
medical decision-maker. Every AI/OCR result in this app is treated as a
suggestion the patient must review — nothing is silently promoted to
"verified" data. This document explains how that's implemented, not just
asserted.

## 0. What changed in the document pipeline (v2)

* **Two phases.** Phase 1 (quick, no AI): text layer / Tesseract OCR +
  regex entities, stored immediately as `pending_review`. Phase 2 (optional
  AI, background): an LLM reads the OCR text and returns structured entities
  and a short plain-language summary. The UI polls while `ai_status` is
  `pending`. If AI is off or fails, the phase-1 result stays - nothing is lost.
* **Grounding filter.** Every AI-proposed item must literally appear in the
  document text (normalised: case, spaces, "500 mg" == "500mg"); otherwise it
  is dropped. Schemas have no diagnosis/finding fields; outputs are
  validated by Pydantic and carry a mandatory disclaimer.
* **X-rays / MRI / CT are not OCR material.** OCR reads printed text, not
  anatomy. Those uploads (category `xray`, `mri`, `ct_scan`) are stored
  untouched and shown in an in-app viewer (zoom, rotate, brightness,
  contrast, invert). Only burned-in annotations (L/R, dates, labels) are
  read, and an *optional* vision model (`AI_VISION_ENABLED`) may add purely
  descriptive metadata (modality, body region, view, quality). The app never
  interprets the image. The radiologist's *written report* is text and goes
  through the normal pipeline.
* **Honest statuses.** `ocr_status` is now `completed`, `no_text`,
  `skipped` (OCR disabled), `not_applicable` (image) or `failed` - it no
  longer says "completed" when nothing was read.
* **Plain-language explanation.** `POST /documents/{id}/explain` (explicit
  patient action) explains wording and suggests questions for the doctor.
* **Review before it becomes record.** "Review & add" opens the normal
  medication/allergy/condition form pre-filled; the patient saves it, and
  `source=document_suggestion` + `source_document_id` record provenance.
* **Recovery.** Documents stuck in `processing` after a crash are re-queued
  at startup.

## 1. Document upload -> OCR -> entity extraction

```
Upload (PDF or image)
  |
  v
Determine file type (mime_type)
  |
  +-- PDF --> PyMuPDF (fitz) text extraction
  |             |
  |             +-- has a text layer --> use it directly
  |             +-- no text layer (scanned PDF) --> render pages to images, OCR each
  |
  +-- image --> OCR directly
  |
  v
Tesseract OCR (pytesseract), when OCR_ENABLED=true and the tesseract-ocr
binary is available -- otherwise the engine falls back to a no-op
(NullOCREngine) automatically, with a warning log. The app never fails to
start or fails an upload because of this; the document just won't get
automatic text extraction.
  |
  v
Clean text (collapse whitespace, strip control characters)
  |
  v
Store raw_text + confidence in `document_extractions`
(confidence: 0-1, derived from pytesseract's mean word confidence)
  |
  v
Heuristic entity extraction (regex/keyword-based, NOT an LLM call --
this step works even with AI_ENABLED=false) -> structured JSON:
{
  "medications": [{"name", "dosage", "frequency"}],
  "conditions": [...], "allergies": [...], "procedures": [...],
  "dates": [...], "lab_values": [{"label","value","unit"}],
  "recommendations": [...]
}
  |
  v
document_extractions.status = "pending_review" (ALWAYS -- every extraction
requires patient review; confidence only informs the UI, it never gates
anything automatically)
```

The whole pipeline runs as a FastAPI `BackgroundTasks` job after the
upload response is returned, so uploads never block on OCR. If a patient
has turned off `data_sharing_consent` in their preferences, this pipeline
is skipped entirely for that patient's future uploads
(`ocr_status="skipped"`) — the document still uploads and stores normally.

Why a heuristic extractor and not an LLM call here: it has to work with
the default configuration (`AI_ENABLED=false`), and entity extraction from
OCR text is a narrower, more mechanical problem than summary generation —
regex/keyword matching against a modest curated list is transparent,
fast, and doesn't require a model to be running at all.

**The patient must explicitly review an extraction** (`PATCH
/api/v1/documents/{id}/extraction {"status": "reviewed"|"dismissed"}`).
Reviewing does **not** write anything into `allergies`/`medications`/
`medical_conditions` automatically — the frontend shows the extracted
values so the patient can copy what's accurate into the normal Add
Medication/Allergy/Condition forms themselves. This is a deliberate
one-way door: nothing in this codebase writes AI/OCR output into a
verified table without that explicit, separate patient action.

## 2. Health snapshot (the "verified data" boundary)

A `HealthSnapshot` is an immutable, versioned JSON aggregation of the
patient's **directly-entered** data only: active medications, allergies,
conditions, doctor contacts, and relevant appointments. It never includes
anything from `document_extractions`. A new version is created every time
one of those source tables changes, and old versions are never deleted or
modified — this is what makes "which exact data did this AI summary come
from" always answerable.

## 3. AI summary generation (Ollama)

```
AIProvider (interface)
     |
     v
OllamaProvider  <-- the only concrete implementation wired up; NullAIProvider
                     is used automatically when AI_ENABLED=false so the rest
                     of the app never has a hard Ollama dependency
```

`app/services/ai_summary_service.py` builds a structured prompt
(`app/ai/prompt.py`) from: the latest verified `HealthSnapshot`, the
patient's optional free-text concerns for this visit, recent timeline
entries (capped), and any `document_extractions` the patient explicitly
chose to include as clearly-labeled, non-verified context. The system
instruction is, word for word:

> "You are generating an organizational summary for a healthcare
> professional. Do not diagnose, prescribe, infer unsupported medical
> facts, or invent information. If information is unavailable, say that
> it is unavailable."

...extended with explicit forbidden-content items (diagnosis, prescription
language, medication-change suggestions, claims of medical certainty).

**Structured output + hallucination control**: the model is asked for
JSON matching a fixed shape (`app/ai/schemas.py`'s `StructuredAISummary`),
requested with Ollama's `format: "json"` mode. The response is parsed
defensively (`app/ai/json_utils.py`) and validated with Pydantic. The
`summary` field's validator rejects anything that doesn't start with the
required disclaimer sentence. On invalid/malformed output, the service
retries **once** with a follow-up instruction emphasizing "reply with
ONLY valid JSON" — if that also fails, it raises a clear
`AIGenerationError` (502) rather than ever storing or fabricating a
fallback summary in code.

The model name is always read from `OLLAMA_MODEL` (env var) — never
hardcoded anywhere in the codebase.

## 4. Review workflow (Generate -> Review -> Edit -> Confirm -> Share)

```
generate()  -->  AISummary{status: pending_review, summary_text, model_name, prompt_version}
                        |
                        v (patient edits, optional)
save_edit() -->  AISummary{edited_summary_text set}
                        |
                        v
confirm_review()  -->  AISummary{status: reviewed, reviewed_at: now()}
                        |
                        v
share()  -->  emails edited_summary_text (if set) else summary_text --
              NEVER the raw draft if the patient edited it --
              only allowed once status is "reviewed"; sets status="shared"
              only if the send actually succeeds
```

Both `summary_text` (as generated) and `edited_summary_text` (as approved
by the patient) are stored — the generated draft is never overwritten,
so there's always a record of what the model produced versus what the
patient actually sent.

Whenever a new `HealthSnapshot` is generated, every `pending_review`/
`reviewed` `AISummary` for that patient is marked `outdated` (never
`shared` ones — already-shared history is immutable) — an old summary can
never be re-shared as if it reflected current data without the patient
generating a fresh one first.

## 5. Timeline tagging (hallucination control, patient-facing)

Every entry the timeline surfaces is tagged with exactly one of:

- **VERIFIED** — the patient directly entered this (a condition,
  medication, appointment, doctor contact they typed in themselves).
- **PATIENT_PROVIDED** — a freeform timeline note the patient wrote.
- **AI_EXTRACTED** — sourced from `document_extractions.extracted_data`,
  never upgraded to VERIFIED automatically.
- **UNVERIFIED** — reserved for any future source that doesn't yet fit
  the above (not currently emitted, kept in the tag set for forward
  compatibility per the product spec).

The frontend renders this tag as a visible, color-coded badge on every
timeline entry — an AI-extracted item can never look like a confirmed
fact in the UI.

## Known limitations

- The Ollama integration has not been exercised against a real running
  Ollama server in this development sandbox (none is available here) —
  it's covered by unit/integration tests against a controllable fake
  `AIProvider`, not a live model. Verify against a real Ollama instance
  before relying on it in a demo.
- Entity extraction is a regex/keyword heuristic, not a trained medical
  NLP model — it will miss unusual phrasing and is intentionally
  conservative (it's a starting point for patient review, not a parser
  that claims completeness).
