# Deployment

## Local development (Docker Compose)

```bash
cp .env.example .env
docker compose up --build
```

Starts Postgres, runs Alembic migrations automatically, then starts the
backend (`--reload`, http://localhost:8000) and frontend (`next dev`,
http://localhost:3000) with source bind-mounted for live editing. This is
the dev-oriented compose file — see below for production.

Optional local LLM runtime:

```bash
docker compose --profile ai up ollama
# then set AI_ENABLED=true and restart the backend
```

> **Note on this repository's own build/verification history**: no live
> Docker daemon was available in the sandbox this project was built in, so
> `docker compose up --build` itself has only been *syntax-validated*
> (`docker compose config`), not actually built and run end-to-end in a
> container. Backend and frontend were verified by running them directly
> (`uvicorn`, `next build && next start`) against a real local Postgres
> instance instead — see the root `README.md`'s test/verification
> sections for what *was* actually exercised. Run a real
> `docker compose up --build` smoke test on a machine with Docker before
> considering container support fully verified.

## Production

A separate compose file avoids bind-mounting source and runs real
production builds:

```bash
cp .env.production.example .env.production
# fill in real values: JWT_SECRET_KEY, DATABASE_URL, CORS_ORIGINS,
# NEXT_PUBLIC_API_BASE_URL, SMTP credentials, etc.
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Differences from the dev compose file:
- Backend: no `--reload`, still runs `alembic upgrade head` on boot.
- Frontend: `frontend/Dockerfile`'s multi-stage `production` target
  (`npm run build` at image-build time, `npm run start` at runtime) —
  `NEXT_PUBLIC_API_BASE_URL` is a **build arg**, baked into the client
  bundle, so changing it requires a rebuild, not just an env var change at
  runtime.
- No source bind mounts; the image is the deployable artifact.
- The bundled `db` service is fine for a single-host deployment but has no
  backup/HA story — point `DATABASE_URL` at a managed Postgres instance
  (RDS, Neon, Supabase, etc.) for anything beyond a demo, and remove the
  `db` service from the compose file entirely.

### Reverse proxy / TLS

Neither compose file includes a reverse proxy. For a real deployment, put
nginx/Caddy/Traefik (or your platform's load balancer) in front of both
the `backend` (port 8000) and `frontend` (port 3000) services, terminate
TLS there, and set `CORS_ORIGINS`/`NEXT_PUBLIC_API_BASE_URL` to the public
HTTPS URLs.

### Storage in production

Only the `local` disk `StorageBackend` is implemented so far (see
`backend/app/storage/`). It works for a single, persistent-volume
deployment but does not survive horizontal scaling or ephemeral
filesystems. `.env.production.example` documents the `S3_*` settings the
`Settings` class already accepts — an S3-compatible `StorageBackend`
implementation is a documented next step (the interface/factory are
already in place; only a new concrete class is needed, no service code
changes).

### Email in production

Set `EMAIL_BACKEND=smtp` with real SMTP credentials (or extend
`app/email/factory.py` with a SendGrid/Mailgun implementation — the
interface already supports it, `NotImplementedError` is raised today if
you set `EMAIL_BACKEND=sendgrid`/`mailgun` without implementing one).
Never use `EMAIL_BACKEND=console` outside local development — it only
logs, it never actually sends.

## Database migrations

Migrations are the only way the schema changes, in every environment:

```bash
cd backend && source .venv/bin/activate
alembic upgrade head      # apply all pending migrations
alembic check              # confirm models and migrations agree (no drift)
alembic revision --autogenerate -m "description"   # after a model change
```

The Docker entrypoints (`docker-compose.yml` and `docker-compose.prod.yml`)
both run `alembic upgrade head` automatically before starting the backend
process — a fresh deployment never needs a manual migration step.

## Observability

- `GET /api/v1/health` — liveness (always 200 if the process is up).
- `GET /api/v1/health/ready` — readiness, actually checks the database
  connection (`SELECT 1`), returns 503 with which check failed if not.
  Wire this into your orchestrator's readiness probe, not `/health`.
- Every request gets an `X-Request-ID` (generated if the client didn't
  send one, echoed back in the response header) threaded into that
  request's log lines for correlation — useful when chasing a single
  failed request through logs in production.
- Structured, timestamped log lines to stdout (`app/core/logging.py`);
  point your platform's log collector at container stdout, no special
  log-shipping config is built into the app itself.

## Environment variables

See `.env.example` (development defaults) and
`.env.production.example` (what changes for a real deployment) at the
repo root — both are fully commented. Never commit a real `.env` or
`.env.production` file; both are gitignored.

## Known limitations

- No live Docker daemon smoke test performed in this project's own build
  environment (see the note above) — config-validated only.
- No CI pipeline is set up in this repository (no `.github/workflows` or
  equivalent) — the verification commands in the root `README.md` are
  meant to be run manually or wired into whatever CI system you add.
- No S3 storage backend or SendGrid/Mailgun email backend implemented yet
  (interfaces exist, concrete implementations don't) — local disk +
  SMTP/console are what's actually usable today.
