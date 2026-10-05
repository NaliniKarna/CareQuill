# Database

PostgreSQL. Every table uses a UUID primary key and timezone-aware
timestamps (see `backend/app/models/mixins.py`). Managed entirely through
Alembic migrations — never hand-edit the schema.

## Tables (20 domain tables + `alembic_version`)

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | Account (email, password hash, verified/active flags) | referenced by every `patient_id`/`user_id` FK below |
| `refresh_tokens` | Hashed, rotating refresh tokens | `user_id` -> `users` |
| `email_verification_tokens` | Single-use email verification | `user_id` -> `users` |
| `password_reset_tokens` | Single-use, expiring password reset | `user_id` -> `users` |
| `health_profiles` | Name, DOB, gender, blood group, contact/emergency info | `user_id` -> `users` (1:1) |
| `allergies` | Patient-entered allergies | `patient_id` -> `users` |
| `medical_conditions` | Patient-entered conditions | `patient_id` -> `users` |
| `medications` | Medications (active/inactive, dosage, dates) | `patient_id` -> `users` |
| `medication_reminders` | Time + days-of-week reminder records | `medication_id` -> `medications`, `patient_id` -> `users` |
| `doctor_contacts` | Saved doctor contact info (no doctor accounts) | `patient_id` -> `users` |
| `appointments` | Appointments (scheduled/completed/cancelled/missed) | `patient_id` -> `users`, `doctor_contact_id` -> `doctor_contacts` (nullable) |
| `medical_documents` | Uploaded file metadata (never the raw file itself) | `patient_id` -> `users` |
| `document_extractions` | Raw OCR text + confidence + structured entity JSON | `document_id` -> `medical_documents` |
| `timeline_notes` | Patient-authored freeform timeline notes | `patient_id` -> `users` |
| `health_snapshots` | Immutable, versioned aggregation of verified data | `patient_id` -> `users` |
| `ai_summaries` | Generated + patient-edited AI summary, review status | `patient_id` -> `users`, `health_snapshot_id` -> `health_snapshots` |
| `email_logs` | Every email send attempt (AI summary share, report share) | `patient_id` -> `users`, `appointment_id` -> `appointments` (nullable) |
| `user_preferences` | Notification prefs + data-sharing consent | `user_id` -> `users` (1:1) |
| `audit_logs` | Append-only record of security-relevant actions | `user_id` -> `users` (`SET NULL` on delete) |
| `notifications` | Persisted in-app notifications | `patient_id` -> `users` |

## Design notes

**Everything is scoped by `patient_id`/`user_id`, indexed.** This is the
backbone of the app's authorization model: every repository query filters
by the authenticated user's id, never a client-supplied one. See
`docs/security.md` for how this is tested.

**Verified vs. suggested data lives in different tables.** `allergies`,
`medical_conditions`, `medications`, `doctor_contacts`, and `appointments`
are patient-asserted structured data (what "verified" means in this app —
the patient typed it in themselves). `document_extractions.extracted_data`
is AI/OCR-suggested data and is never written into those tables
automatically; a patient re-enters it themselves through the normal CRUD
forms after reviewing it. This separation is deliberate and enforced at
the service layer, not just documented — see `docs/ai-pipeline.md`.

**Immutable, append-only tables**: `health_snapshots` and `audit_logs` have
no `update`/`delete` repository methods at all — by design, not oversight.
A new snapshot version is created on every verified-data change; old ones
are never touched. Audit log rows are permanent history.

**Denormalization for history integrity**: `email_logs` stores
`doctor_name`, `appointment_date`, and `appointment_reason` at send time
(not just foreign keys) so the sharing history stays accurate even if the
doctor contact or appointment is later edited or deleted.

## Migrations

Four Alembic revisions so far, applied in order:

1. `929a71e5ab2b` — initial schema (Checkpoint 1: users through email_logs,
   14 tables)
2. `aa8aa52fe4ac` — medical records/OCR, medications+reminders, allergies,
   conditions, doctors, appointments, timeline, health snapshots
   (Checkpoint 2)
3. `ef4a04efe62e` — `ai_summaries.edited_summary_text` (Checkpoint 2)
4. `a39b467114ed` — reports/notifications/preferences/audit_logs, plus
   `email_logs` reporting columns (Checkpoint 3)

Run `alembic upgrade head` to apply all of them to a fresh database, and
`alembic check` to confirm the models and the migrations agree (run as
part of this repo's standard verification, see the root `README.md`).
