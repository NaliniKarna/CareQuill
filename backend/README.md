# MedQueue AI — Backend

FastAPI backend for MedQueue AI. See the [repo-root README](../README.md)
for full setup instructions (Docker Compose and manual dev). This file is
a quick reference for working in this directory specifically.

## Layout

```
app/
├── api/
│   ├── dependencies/   FastAPI dependencies (DB session, current-user auth)
│   └── v1/             Route modules, aggregated in router.py
├── core/                config, security (hashing/JWT), logging, exceptions
├── db/                  SQLAlchemy engine/session, declarative base
├── models/               SQLAlchemy ORM models (one file per table)
├── schemas/              Pydantic request/response schemas
├── repositories/         Database access only — no business logic
├── services/             Business logic — called by routes, calls repositories
├── ai/                   AI provider interface + Ollama/null implementations,
│                          structured prompt building + JSON validation
├── ocr/                  OCR engine interface + Tesseract/null implementations
├── pdf/                  PDF report generator interface + ReportLab implementation
├── email/                Email sender interface + SMTP/console implementations,
│                          email templates
├── storage/               File storage interface + local-disk implementation
├── utils/                 Shared helpers (e.g. safe filename handling, MIME sniffing)
└── main.py                FastAPI app assembly (middleware, routers, lifespan)
alembic/                  Migrations
tests/                     Pytest suite (runs against a real Postgres test DB)
```

Routes never contain business logic; services never talk to the database
directly (they go through repositories); AI/OCR/PDF/email/storage are only
ever used behind their interface, never imported directly by services —
this is what lets any of them be swapped later without touching the rest
of the app.

## Common commands

```bash
source .venv/bin/activate

alembic upgrade head                       # apply migrations
alembic revision --autogenerate -m "..."    # generate a new migration after model changes
alembic check                                # verify no un-migrated model changes

uvicorn app.main:app --reload                # run the dev server

pytest                                        # run tests
pytest -k test_login_success -v               # run one test

ruff check app tests                          # lint
ruff check app tests --fix                    # lint, autofixing what it can
mypy app                                      # type check
```

## Tests

`tests/conftest.py` points the app at `TEST_DATABASE_URL` (a separate
database from your dev one), recreates the schema once per test session,
and truncates all tables between tests. Tests run against real
PostgreSQL — not SQLite or mocks — so async-driver/database-constraint
issues surface in CI the same way they would in production.

141+ tests as of the latest checkpoint, including an explicit IDOR
(cross-patient access) test for every resource, file-upload validation
tests (size, extension, magic-byte spoofing, path traversal), OCR
pipeline tests, AI-response validation/retry tests (against a fake
`AIProvider`, since no live Ollama server runs in CI/this sandbox), PDF
report generation tests, and email-service tests. See
[`../docs/security.md`](../docs/security.md) for what the security-audit
pass specifically checked.
