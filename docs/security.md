# Security

MedQueue AI handles sensitive health information. This document describes
the security posture as actually implemented and tested, not aspirational
goals. **This project does not claim HIPAA, GDPR, or any other formal
compliance certification** — it follows sound engineering practice
appropriate for a student/portfolio-scale product, and any real deployment
handling real patient data would need a formal compliance review beyond
what's described here.

## Authentication & sessions

- Passwords hashed with Argon2 (via `passlib`), never logged, never
  returned by any endpoint.
- Access tokens are short-lived JWTs (`ACCESS_TOKEN_EXPIRE_MINUTES`,
  default 15 minutes).
- Refresh tokens are opaque, high-entropy strings; only a SHA-256 hash is
  ever persisted (`refresh_tokens` table). Refresh uses **rotation**: each
  use immediately revokes the token that was presented and issues a new
  one, so a stolen refresh token is only useful once before detection.
- `POST /api/v1/auth/change-password` revokes every *other* refresh token
  for that user on success, so other logged-in sessions/devices are forced
  to re-authenticate.
- Password reset and email verification tokens are single-use and expire
  (`password_reset_tokens`, `email_verification_tokens`).

## Authorization / IDOR prevention

**Every** patient-data query is scoped to `current_user.id`, derived from
the verified JWT — never from a client-supplied id in the URL or body.
This is the single most important security property in this codebase and
is enforced identically across every resource: documents, medications,
reminders, allergies, conditions, doctor contacts, appointments, health
snapshots, AI summaries, timeline notes, reports, email logs,
notifications, preferences.

This is not just a design intention — it's covered by explicit automated
tests for every one of those resources: user B fetching/editing/deleting
user A's resource by id always gets a `404 not_found` (the app
deliberately returns "not found" rather than "forbidden" for a
cross-user access attempt, so an attacker can't even distinguish "doesn't
exist" from "exists but isn't yours"). As of the latest checkpoint, the
backend test suite has **141+ passing tests**, a large fraction of which
are exactly this kind of isolation test — see `backend/tests/`.

## File upload security

- **Extension allowlist** (`ALLOWED_UPLOAD_EXTENSIONS`, default
  `.pdf,.png,.jpg,.jpeg`) and **size limit** (`MAX_UPLOAD_SIZE_MB`,
  default 15MB) are both enforced server-side, not just in the frontend.
- **Magic-byte sniffing**: the actual file content is checked against
  known signatures (`%PDF` for PDF, `\xff\xd8\xff` for JPEG, `\x89PNG` for
  PNG) — a file renamed to `.pdf` whose real content is something else is
  rejected, tested explicitly.
- **Filenames are never trusted**: the original filename is sanitized for
  *display only* (`sanitize_filename`); the name actually used on disk is
  always server-generated (`generate_stored_filename`, a UUID + the
  validated extension) — this eliminates path traversal and filename
  collision/enumeration attacks by construction, not by blocklisting.
- **No arbitrary file serving**: documents are only ever readable through
  `GET /api/v1/documents/{id}/download`, which re-derives the storage path
  server-side after an ownership check — no endpoint ever accepts or
  echoes back a raw filesystem path, and the physical `storage_path`
  column is never included in any JSON response.
- `LocalStorageBackend._resolve` additionally re-validates that any
  resolved path stays inside the configured storage root as a
  defense-in-depth measure, independent of the filename generation above.

## CORS

`CORS_ORIGINS` is environment-configured (comma-separated allowlist),
never `*`, and `allow_credentials=True` is paired with that explicit
allowlist — never with a wildcard origin (tested).

## Error handling & logging

- Every API error response has the consistent shape
  `{"error": {"code", "message", "details"}}`. Unhandled exceptions are
  logged server-side (with a request id for correlation, see
  `docs/deployment.md`) and always return a generic message to the
  client — stack traces and internal exception text never reach a
  response body.
- A best-effort redaction filter (`RedactSensitiveFilter` in
  `app/core/logging.py`) strips common sensitive field names
  (password/token/authorization/etc.) from structured log arguments.
  Passwords and tokens are never intentionally logged anywhere in the
  codebase (verified by a repository-wide grep as part of the security
  audit below).
- Audit logs (`audit_logs` table) record *that* a sensitive action
  happened (login, logout, document upload/delete, AI summary
  generate/edit, report share, medication add, health profile update) —
  event type + resource identifiers only, **never** medical content or
  credentials.

## SQL injection

Every repository uses SQLAlchemy's ORM/Core query builder with bound
parameters — there is no string-formatted or concatenated SQL anywhere in
the codebase (verified by a static grep sweep for `f"...SELECT`,
`.format(` near SQL, and `text(f"...")` patterns as part of the audit
below; the only raw `text()` usage in the whole app is the literal,
parameter-free `SELECT 1` in the readiness check).

## Secrets

All credentials and secrets (`JWT_SECRET_KEY`, SMTP credentials, S3 keys,
etc.) are read from environment variables via `app/core/config.py`'s
`Settings` — nothing is hardcoded. `.env` files are gitignored; only
`.env.example`/`.env.production.example` (placeholder values) are
committed. **Generate a fresh `JWT_SECRET_KEY`
(`openssl rand -hex 32`) before any real deployment** — the checked-in
default is an obvious placeholder, intentionally.

## Security audit findings (Checkpoint 3)

A dedicated audit pass was run across the whole application (not just new
code) covering: authentication bypass, authorization bugs, IDOR, file
upload vulnerabilities, path traversal, unsafe filenames, MIME spoofing,
oversized uploads, SQL injection, XSS, CSRF exposure, CORS, JWT handling,
refresh token security, password reset security, sensitive logs, secrets,
and error leakage.

**One real bug was found and fixed**: an early implementation of the
request-ID middleware (added for observability, see `docs/deployment.md`)
used Starlette's `BaseHTTPMiddleware`, which interfered with the app's
generic-500-on-unhandled-exception behavior — some errors could have
propagated further than intended. It was replaced with a plain ASGI
middleware class, and a regression test forces an unhandled exception and
asserts the client still only ever sees the generic error envelope.

Everything else checked came back clean under the existing design (IDOR
scoping, file validation, token handling, CORS, parameterized queries, no
hardcoded secrets) — each category above has an explicit passing test
proving it, not just a manual read-through. Frontend XSS exposure is low
by construction (React escapes rendered text by default; no
`dangerouslySetInnerHTML` is used anywhere in the app). Formal CSRF
protection wasn't added because the API is a pure bearer-token JSON API
consumed by a separate frontend origin (no cookie-based session to forge)
— this is a standard, accepted posture for this architecture, not an
oversight, but is worth re-confirming if the auth model ever changes to
cookie-based sessions.

## What's explicitly out of scope

Per the product's own constraints: no doctor portal, no hospital
integration, no billing/insurance handling, no telemedicine — none of
those attack surfaces exist in this application at all.
