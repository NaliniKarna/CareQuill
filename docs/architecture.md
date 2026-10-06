# Architecture

CareQuill is a **modular monolith**, not a microservices system. One
backend deployment, one frontend deployment, one database. The
"modular" part is about internal boundaries, not separate services.

## Why a modular monolith

At this project's scale (a final-year / portfolio-sized product), separate
services would add operational complexity (service discovery, network
calls, distributed transactions) without a corresponding benefit. A
modular monolith gets most of the benefits people reach for
microservices for — replaceable pieces, clear ownership boundaries,
independent testability — while staying simple to run, deploy, and reason
about. If a piece genuinely needs to scale independently later (OCR
processing, for example), it can be extracted then, because the
boundaries already exist in the code.

## Backend layering

```
API (routes)  →  Service  →  Repository  →  Database
```

- **Routes** (`app/api/v1/*.py`) parse the request, call exactly one
  service method, and shape the response. No business logic, no direct
  database access.
- **Services** (`app/services/*.py`) hold business logic: what "logging
  in" means, what fields make up profile completion, how token rotation
  works. Services call repositories, never the ORM directly.
- **Repositories** (`app/repositories/*.py`) are the only code that
  issues SQLAlchemy queries. They know about tables and columns; they
  don't know about HTTP or business rules.
- **Models** (`app/models/*.py`) are the SQLAlchemy ORM definitions — the
  schema, expressed in Python.

This means: to find out what an endpoint actually does, read the service.
To find out how something is stored, read the repository and the model.
To change how login works without changing how it's exposed over HTTP,
you only touch the service.

## External integrations are interfaces, not calls

AI (`app/ai`), OCR (`app/ocr`), PDF generation (`app/pdf`), email
(`app/email`), and file storage (`app/storage`) are each defined as an
abstract interface plus one or more implementations, selected by a small
`factory.py` that reads configuration:

- `AI_PROVIDER=ollama` (default) or the app can run with `AI_ENABLED=false`
  entirely — no code path requires an LLM to be running.
- `EMAIL_BACKEND=console` (logs instead of sending — the default for local
  dev) vs `smtp` vs a future `sendgrid`/`mailgun` implementation.
- `STORAGE_BACKEND=local` (the only implementation so far) vs a future
  `s3` implementation.

Services depend only on the interface (`AIProvider`, `EmailSender`,
`StorageBackend`, `OCREngine`). None of them import Ollama, smtplib, or
the filesystem directly. Swapping SMTP for SendGrid, or local disk for
S3, means writing one new implementation file and changing an environment
variable — no service code changes.

## Database

PostgreSQL, UUID primary keys, timezone-aware timestamps everywhere.
Structured relational tables for each domain concept (allergies,
conditions, medications, doctor contacts, appointments, documents) rather
than one large JSON blob — this keeps the data queryable, constrainable
(foreign keys, `ondelete` rules), and independently indexable.

Two tables exist beyond the original spec's list, both justified by
explicit "Authentication" requirements rather than added speculatively:
`email_verification_tokens` and `password_reset_tokens`. They follow the
same pattern as `refresh_tokens` — only a hash of the opaque token is
ever stored, never the plaintext.

`document_extractions`, `health_snapshots`, and `ai_summaries` model the
"AI output is a suggestion, not a fact" rule directly in the schema: OCR
and AI results live in their own tables, separate from the verified
structured tables (allergies, conditions, medications). Nothing writes
from an extraction into a verified table automatically — that is enforced
at the service layer (see `docs/ai-pipeline.md` for the full pipeline and
`docs/security.md` for how patient isolation is enforced and tested).

`audit_logs` and `notifications` (added alongside reports/preferences)
follow the same pattern as everything else here: a repository/service per
resource, `patient_id`/`user_id`-scoped, no exceptions. `audit_logs` is
additionally append-only (no update/delete repository methods), same as
`health_snapshots`, since both are meant to be permanent history.

## Frontend structure

Feature-based organization under `frontend/src/`:

- `app/` — Next.js App Router routes only (thin: import a feature
  component and render it).
- `features/<name>/` — the actual UI and logic for one feature area
  (forms, feature-specific components).
- `components/ui/` — generic, reusable primitives (button, input, card,
  ...), hand-built in the shadcn/ui style (Radix primitives + Tailwind +
  class-variance-authority) since this environment could not reach
  `ui.shadcn.com`'s registry at build time.
- `services/` — one file per backend resource, wrapping the API client.
- `store/` — Zustand stores (currently: auth).
- `hooks/` — cross-cutting React hooks (currently: `useAuth`).
- `lib/` — the configured axios client (token attach + refresh-on-401 +
  single-flight refresh), plus small utilities.

Authentication state is a short-lived access token (kept in memory /
persisted store) plus a refresh token, with automatic silent refresh on a
401 and a single in-flight refresh shared across concurrent requests.
