# CareQuill

 CareQuill helps patients organize and communicate their health history
to doctors. Patients keep their health profile, allergies, conditions,
medications, medical documents, doctor contacts, and appointments in one
place they control, get AI-assisted help organizing and summarizing that
information, and can generate a professional PDF health report to share
with a doctor by email — always after reviewing and approving what's sent.

**Positioning:** *Your health history, intelligently organized for every
consultation.*

> CareQuill is an organizational and communication assistant. It does
> not diagnose conditions, prescribe treatment, or act as an autonomous
> medical decision-maker. It is designed with privacy and security
> principles appropriate for handling sensitive health information, but it
> is a student/portfolio project and does **not** claim HIPAA, GDPR, or
> any other formal compliance certification.

It is explicitly **not**: a diagnostic system, an autonomous medical
agent, a hospital management system, an electronic health record
replacement, or a prescription system. No doctor portal, no billing, no
insurance, no telemedicine, no wearable integration, no vector database.
Keeping scope controlled is a deliberate product decision, not something
still to be added.

## Project status

Three checkpoints, all implemented and verified against a real Postgres
database (not mocks):

1. **Foundation** - auth (register/login/refresh/logout/forgot-reset/
   verify), health profile, a basic dashboard.
2. **Core functionality** - medical records + OCR + heuristic entity
   extraction, medications + reminders, allergies, conditions, doctor
   contacts, appointments, a tagged health timeline, versioned health
   snapshots, and AI-assisted summaries with a full
   Generate → Review → Edit → Confirm → Share workflow.
3. **Reports, security, and polish** - PDF health report generation with
   patient-controlled section selection, a Share-With-Doctor flow that
   emails the PDF plus explicitly-selected documents, email history,
   in-app notifications, an audit log, account settings (change password,
   notification/privacy preferences), request-id'd structured logging, a
   readiness endpoint, a public landing page, mobile navigation, and a
   dedicated security audit pass.



## Features

- **Auth**: register/login/refresh/logout, forgot/reset password, email
  verification, change password (revokes other sessions).
- **Health profile**: identity, contact, emergency contact, height/weight.
- **Medical records**: upload PDF/image (10 categories), background OCR
  (PyMuPDF + Tesseract) with heuristic entity extraction, patient review
  workflow, authorized download, search/filter, delete.
- **Medications**: full CRUD, activate/deactivate, reminders (time +
  days-of-week records).
- **Allergies, conditions, doctor contacts, appointments**: full CRUD,
  patient-isolated, validated.
- **Health timeline**: chronological, every entry tagged VERIFIED /
  PATIENT_PROVIDED / AI_EXTRACTED / UNVERIFIED.
- **Health snapshots**: immutable, versioned, auto-regenerated on verified
  data changes.
- **AI health summaries**: Ollama-backed, structured JSON output validated
  with Pydantic (safe retry on malformed output), full review workflow.
- **PDF health reports**: patient chooses exactly what's included
  (conditions/allergies/medications/timeline/patient notes/AI summary/
  specific documents); nothing is shared automatically.
- **Share with doctor**: email the PDF (+ explicitly selected documents)
  to a saved doctor contact, with a full send history.
- **Notifications**: appointment-approaching, medication reminders due,
  AI summary ready, document processed, report shared, email failures.
- **Settings**: account info, change password, notification preferences,
  a privacy control over whether uploads get OCR/AI-processed at all.
- **Dashboard**: profile completion, upcoming appointment, active
  medication count, recent records, latest snapshot/AI-summary status,
  reminders due, quick actions.

## Architecture

Modular monolith: one backend deployment, one frontend deployment, one
database — internal module boundaries instead of network boundaries. Full
rationale in [`docs/architecture.md`](./docs/architecture.md).

```
API (routes)  →  Service  →  Repository  →  Database
```

AI, OCR, PDF generation, email, and file storage are each an interface
plus a swappable implementation selected by environment configuration —
see `backend/app/{ai,ocr,pdf,email,storage}`. See
[`docs/ai-pipeline.md`](./docs/ai-pipeline.md) for the OCR/entity-
extraction/AI-summary pipeline in detail, and
[`docs/database.md`](./docs/database.md) for the schema.

## Technology stack

**Frontend:** Next.js (App Router) · TypeScript · Tailwind CSS ·
hand-rolled shadcn/ui-style components (Radix primitives + CVA) · React
Hook Form · Zod · TanStack Query · Zustand · Lucide icons

**Backend:** Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.x (async) ·
asyncpg · Alembic · PostgreSQL · JWT auth · Argon2 password hashing ·
ReportLab (PDF) · PyMuPDF + Tesseract/pytesseract (OCR) · Pytest

**AI / OCR / PDF / Email / Storage:** isolated behind interfaces so
Ollama/local-disk/SMTP can be swapped for other providers via
configuration alone. The app runs fully without AI or OCR configured
(`AI_ENABLED=false`, `OCR_ENABLED=false` by default).

## Repository structure

```
CareQuill/
├── backend/                 FastAPI app (see backend/README for its own layout)
├── frontend/                Next.js app (feature-based structure under src/)
├── docs/
│   ├── architecture.md       layering + interface/factory rationale
│   ├── database.md           schema, tables, migrations
│   ├── api.md                full endpoint reference
│   ├── ai-pipeline.md        OCR -> extraction -> AI summary, in detail
│   ├── security.md           auth, IDOR prevention, file/upload safety, audit findings
│   └── deployment.md         local, Docker, and production deployment
├── scripts/                  Helper scripts (local DB bootstrap)
├── .env.example               Development environment variable reference
├── .env.production.example    Production environment variable reference
├── docker-compose.yml         Local development (bind-mounted source, --reload)
├── docker-compose.prod.yml    Production (built images, no bind mounts)
└── README.md                  This file
```

## Quick start with Docker Compose

Prerequisites: Docker and Docker Compose.

```bash
git clone <this-repo> medqueue-ai
cd medqueue-ai
cp .env.example .env
docker compose up --build
```

This starts PostgreSQL, runs Alembic migrations automatically, and starts
the backend (http://localhost:8000) and frontend (http://localhost:3000).

- API docs (Swagger UI): http://localhost:8000/api/v1/docs
- Frontend: http://localhost:3000

To also run a local Ollama instance for AI features (optional, not
required for the app to run):

```bash
docker compose --profile ai up ollama
```

Then set `AI_ENABLED=true` in `.env` and restart the backend.

For production deployment (built images, no bind mounts, real production
build of the frontend), see [`docs/deployment.md`](./docs/deployment.md).

## Manual local development (without Docker)

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (running locally, or via `docker compose up db`)
- Optional but recommended for real OCR: the `tesseract-ocr` system
  package (`apt-get install tesseract-ocr` / `brew install tesseract`) —
  without it, uploads still work, they just skip automatic text
  extraction (see `docs/ai-pipeline.md`).

### 1. Database

Create the database and a matching user (adjust to taste; must match your
`.env`):

```sql
CREATE USER medqueue WITH PASSWORD 'medqueue_dev_pw' CREATEDB;
CREATE DATABASE medqueue_ai OWNER medqueue;
CREATE DATABASE medqueue_ai_test OWNER medqueue;  -- used by the backend test suite
```

(`scripts/create_dev_db.sql` does exactly this.)

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

cp ../.env.example .env
# edit backend/.env: DATABASE_URL / TEST_DATABASE_URL should point at
# localhost (the .env.example default already does)

alembic upgrade head                # run migrations
uvicorn app.main:app --reload       # http://localhost:8000
```

Verification (run after any backend change):

```bash
alembic check           # confirm models and migrations agree
ruff check app tests    # lint
mypy app                 # type check
pytest -q               # 141+ tests: auth, every resource's CRUD + IDOR,
                         # file validation, OCR pipeline, AI validation/
                         # retry, PDF/report generation, email service,
                         # security-audit regression tests
```

### 3. AI setup (Ollama) — optional

The app runs fully with `AI_ENABLED=false` (the default) — AI summaries
are simply unavailable, everything else works. To enable them locally:

```bash
# install Ollama: https://ollama.com
ollama pull llama3.2        # or any model you prefer
ollama serve                 # http://localhost:11434
```

Then in `backend/.env`:

```
AI_ENABLED=true
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

Restart the backend. The model name is always read from `OLLAMA_MODEL` —
never hardcoded — so any locally-pulled model works without a code
change. See [`docs/ai-pipeline.md`](./docs/ai-pipeline.md) for exactly how
the prompt is built and how malformed output is handled.

### 4. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local 2>/dev/null || true   # or create manually, see below
npm run build && npm run start      # production build+serve, http://localhost:3000
```

`frontend/.env.local`:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

> This repo's own development used `npm run build && npm run start`
> rather than `npm run dev` for verification, because `next dev`'s HMR
> websocket didn't work reliably in the sandbox this project was built
> in. `npm run dev` should work fine on a normal developer machine; if
> forms seem unresponsive in dev mode, try the production build as a
> sanity check first.

Frontend verification:

```bash
npm run lint            # eslint
npx tsc --noEmit         # typecheck
npm run build            # production build
```

## Environment variables

See [`.env.example`](./.env.example) (development) and
[`.env.production.example`](./.env.production.example) (production) at
the repo root for the full, documented list. Values in `.env.example` are
safe local-development defaults; **never commit a real `.env` or
`.env.production` file** (both are gitignored), and generate a fresh
`JWT_SECRET_KEY` (`openssl rand -hex 32`) before deploying anywhere real.

## Database migrations

Alembic-managed, never hand-edited. `alembic upgrade head` applies
everything; `alembic check` confirms there's no drift between the models
and the migration history. Full table-by-table reference:
[`docs/database.md`](./docs/database.md).

## API reference

Full endpoint list with request/response notes:
[`docs/api.md`](./docs/api.md). Interactive OpenAPI docs (Swagger UI),
organized by tag (Authentication, Health Profile, Medical Records,
Medications, Conditions, Allergies, Appointments, Doctor Contacts,
Timeline, Health Snapshots, AI, Reports, Email, Preferences,
Notifications, Audit, Dashboard, System):
http://localhost:8000/api/v1/docs

## Testing

Backend: `pytest -q` from `backend/` with the venv active, run against a
**real** local PostgreSQL test database (not SQLite or mocks) — 141+
tests covering authentication, patient isolation (IDOR) for every
resource, CRUD, file upload validation (size/extension/magic-byte/path-
traversal), the OCR pipeline, AI response validation and retry, PDF/report
generation, the email service, and dashboard/appointment logic. `ruff
check` and `mypy app` are both clean.

Frontend: `npm run lint`, `npx tsc --noEmit`, and `npm run build` are all
clean (19+ routes build successfully). There is no dedicated frontend
unit-test runner configured in this project; frontend correctness was
verified with a full end-to-end Playwright run driving the actual
production build through the complete user journey (register → login →
complete profile → add condition/allergy/medication/doctor → book
appointment → upload a report → OCR/entity-extraction completes →
generate a health snapshot → attempt an AI summary → view reports/
settings → logout → confirm the protected-route redirect) with the
results checked directly against the database afterward, not just
"the page didn't crash."

## Deployment

See [`docs/deployment.md`](./docs/deployment.md) for the full walkthrough
(local Docker Compose, production Docker Compose with real builds and no
bind mounts, reverse proxy/TLS notes, storage/email production
configuration, and this project's own honest note about what container
deployment actually was and wasn't verified in its build environment).

## Security considerations

See [`docs/security.md`](./docs/security.md) for the full picture: Argon2
password hashing, short-lived JWTs with rotating single-use refresh
tokens, IDOR prevention enforced and tested on every single resource,
file-upload validation (size/extension/magic-byte/path-traversal), a
consistent no-leak error envelope, an append-only audit log, and the
explicit findings of a dedicated security-audit pass (including one real
bug it found and fixed).

## Known limitations

- No live Docker daemon was available in this project's build
  environment — `docker compose up --build` is config-validated, not
  actually built/run in a container here. Do a real smoke test on a
  machine with Docker before relying on it for a demo.
- No S3 storage backend or SendGrid/Mailgun email backend implemented yet
  (interfaces exist, only local-disk storage and SMTP/console email are
  concrete today).
- The Ollama AI integration is tested against a controllable fake
  provider, not a live Ollama server (none was running in the sandbox) —
  verify against a real model before a live demo if you plan to show AI
  summaries.
- Entity extraction is a regex/keyword heuristic, not a trained medical
  NLP model.
- No push notifications for reminders — dashboard/in-app records only, by
  explicit MVP scope.
- No CI pipeline configured in this repository yet.

## License

Student / portfolio project. No license has been chosen yet.
