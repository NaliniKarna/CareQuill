# API reference

All endpoints are versioned under `/api/v1`. Full interactive OpenAPI docs
(with per-endpoint descriptions) are always available at
`http://localhost:8000/api/v1/docs` when the backend is running.

Every endpoint below except `Authentication` and `System` requires a valid
`Authorization: Bearer <access_token>` header, and every response is
implicitly scoped to the authenticated patient — there is no way to pass a
different user's id and get their data (see `docs/security.md`).

## System

```
GET  /api/v1/health          liveness -- always 200 if the process is up
GET  /api/v1/health/ready    readiness -- checks the DB connection, 503 if not reachable
```

## Authentication

```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh          rotates the refresh token (old one is revoked)
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/forgot-password
POST /api/v1/auth/reset-password
POST /api/v1/auth/verify-email
POST /api/v1/auth/change-password  revokes every OTHER refresh token on success
```

## Health Profile

```
GET  /api/v1/profile
PUT  /api/v1/profile   upsert semantics
```

## Medical Records

```
POST   /api/v1/documents                       multipart upload
GET    /api/v1/documents                       ?category=&processing_status=&q=&limit=&offset=
GET    /api/v1/documents/{id}
GET    /api/v1/documents/{id}/download          streams the file; never exposes the storage path
DELETE /api/v1/documents/{id}
GET    /api/v1/documents/{id}/extraction        OCR text + structured entity suggestions
PATCH  /api/v1/documents/{id}/extraction        mark reviewed/dismissed (never auto-applies data)
```

Categories: `prescription, blood_test, lab_report, xray, mri, ct_scan,
discharge_summary, vaccination, referral, other`.

## Medications

```
POST   /api/v1/medications
GET    /api/v1/medications                      ?active=true|false&q=
GET    /api/v1/medications/{id}
PUT    /api/v1/medications/{id}
DELETE /api/v1/medications/{id}
PATCH  /api/v1/medications/{id}/activate
PATCH  /api/v1/medications/{id}/deactivate

POST   /api/v1/medications/{id}/reminders
GET    /api/v1/medications/{id}/reminders
PATCH  /api/v1/medications/{id}/reminders/{reminder_id}
DELETE /api/v1/medications/{id}/reminders/{reminder_id}
```

## Allergies, Conditions, Doctor Contacts

Identical CRUD shape on each:

```
POST/GET/PUT/DELETE  /api/v1/allergies[/{id}]
POST/GET/PUT/DELETE  /api/v1/conditions[/{id}]
POST/GET/PUT/DELETE  /api/v1/doctors[/{id}]
```

## Appointments

```
POST   /api/v1/appointments
GET    /api/v1/appointments                     ?filter=upcoming|past
GET    /api/v1/appointments/{id}
PUT    /api/v1/appointments/{id}
DELETE /api/v1/appointments/{id}
PATCH  /api/v1/appointments/{id}/cancel
PATCH  /api/v1/appointments/{id}/complete
PATCH  /api/v1/appointments/{id}/miss
```

## Health Timeline

```
GET    /api/v1/timeline                         ?type=&date_from=&date_to=
POST   /api/v1/timeline/notes
GET    /api/v1/timeline/notes
DELETE /api/v1/timeline/notes/{id}
```

Every entry is tagged `VERIFIED | PATIENT_PROVIDED | AI_EXTRACTED |
UNVERIFIED` — see `docs/ai-pipeline.md` for what each tag means.

## Health Snapshots

```
POST /api/v1/health-snapshots/generate    also auto-triggered on verified-data changes
GET  /api/v1/health-snapshots             version list (lightweight)
GET  /api/v1/health-snapshots/latest
GET  /api/v1/health-snapshots/{id}
```

## AI Summaries

```
POST  /api/v1/ai-summaries/generate    body: {patient_concerns?, include_document_ids?}
GET   /api/v1/ai-summaries
GET   /api/v1/ai-summaries/{id}
PATCH /api/v1/ai-summaries/{id}        body: {edited_summary_text}
POST  /api/v1/ai-summaries/{id}/confirm
POST  /api/v1/ai-summaries/{id}/share  body: {doctor_contact_id} -- text-only email
```

## Reports (PDF health summary + share with doctor)

```
POST /api/v1/reports/preview   returns a human-readable preview, sends nothing
POST /api/v1/reports/generate  returns the actual PDF (application/pdf)
POST /api/v1/reports/share     generates the PDF, emails it + any selected
                                 documents, and logs the send
```

All three take the same request shape: `doctor_contact_id`,
`appointment_id?`, section flags (conditions/allergies/medications/
timeline/patient_notes/ai_summary), `ai_summary_id?` (must be `reviewed` or
`shared`, never `pending_review`), `document_ids[]` (explicit opt-in,
never "all documents").

## Email

```
GET /api/v1/email-logs    history: doctor, appointment, date, status,
                            report name -- metadata only, never content
```

## Notifications

```
GET   /api/v1/notifications          ?unread_only=true
PATCH /api/v1/notifications/{id}/read
```

Persisted types (`ai_summary_ready`, `document_processed`,
`report_shared`, `email_failure`) can be marked read. Computed types
(`appointment_approaching`, `medication_reminder`) are generated fresh on
every request and always considered unread — there is nothing to mark.

## Preferences

```
GET /api/v1/preferences
PUT /api/v1/preferences   notification_prefs (per-type booleans),
                            data_sharing_consent (gates OCR/AI processing
                            of future uploads when false)
```

## Audit

```
GET /api/v1/audit-logs    self-only, paginated; event type + resource,
                            never medical content or credentials
```

## Dashboard

```
GET /api/v1/dashboard
```

## Error shape

Every error response, whatever the status code, has this shape:

```json
{"error": {"code": "not_found", "message": "Human-readable message safe to show the user", "details": null}}
```

Unhandled exceptions are logged server-side with full detail (including a
request id, see `docs/deployment.md`'s observability note) and always
return the generic `internal_error` shape to the client — never a stack
trace or raw exception text.
