# Gap analysis: Med AI project description vs. the codebase

Status legend: DONE (already there), FIXED (done in this change set),
OPEN (still missing).

| # | Requirement (from the project description) | Status | Notes |
|---|---|---|---|
| 1 | Secure records: medications, allergies, conditions, documents, doctors, appointments | DONE | CRUD + ownership checks; cross-user access returns 404. |
| 2 | OCR + AI to organise and summarise patient information | FIXED | AI was only in the summary page. Now also reads documents (entity extraction), explains them, and describes images (optional). |
| 3 | AI/OCR output is a suggestion until the patient reviews it | FIXED | Was "mark reviewed" only. Now "Review & add" pre-fills the normal form; nothing is created automatically; provenance stored. |
| 4 | Preserve original uploaded documents | DONE | Stored unchanged; new in-app viewer shows the original. |
| 5 | X-ray / scan handling | FIXED | Previously run through OCR and labelled "completed" with garbage/empty text. Now a separate imaging path (see ai-pipeline.md). |
| 6 | AI never diagnoses | FIXED | Schemas have no diagnosis fields, grounding filter, disclaimers, imaging "interpretation: not_performed". |
| 7 | Health summary PDFs + share with doctors by email | DONE | ReportLab PDF + email log. SendGrid/Mailgun were declared in config but not implemented: FIXED (HTTP providers added). |
| 8 | Production quality: modular, secure, scalable | FIXED (partly) | Event-loop blocking removed, pool config, middlewares, rate limits, prod config guard, non-root multi-stage images. |
| 9 | Fast page loads | FIXED | See CHANGES.md (backend, frontend, Docker). |
| 10 | Provenance of records (manual vs from document) | FIXED | New columns + migration `b7c1d2e3f4a5`. |
| 11 | S3 / object storage | OPEN | Config exists, only local storage implemented. |
| 12 | Encryption at rest for documents | OPEN | Rely on disk/volume encryption for now. |
| 13 | Account data export & deletion (patient control of data) | FIXED | `GET /account/export` (ZIP: JSON + original files), `POST /account/delete` (password + "DELETE"; DB cascade, files removed after commit). UI: Settings > Your data. |
| 14 | Tokens in localStorage | OPEN | Works, but httpOnly cookies are safer against XSS. |
| 15 | Rate limiter is per process | OPEN | Fine for one host; use Redis for several replicas. |
| 16a | Doctor can reply to the patient | FIXED | Shared emails now carry `Reply-To` = patient's email and name the sender. |
| 16 | Appointment reminders / email notifications delivery | OPEN | In-app notifications exist; scheduled email reminders need a worker. |
| 17 | Frontend automated tests | OPEN | Backend has 192 tests; frontend has none. |
| 18 | CI pipeline | OPEN | No workflow file. |
| 19 | Live Ollama / Docker verification | OPEN | Not testable in the sandbox (no Ollama, no Docker daemon). |
