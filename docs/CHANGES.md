# Change set summary

## X-ray / OCR question
OCR cannot read X-rays: it converts printed text to text, and an X-ray is
anatomy. The old code ran such files through OCR and reported "completed".
Now: imaging uploads are stored untouched, viewable in-app, annotation text
is read, an optional vision model adds descriptive metadata only, and the
user is told to upload the radiologist's written report for clinical content.

## Where AI is now used (all suggestion-only)
1. Document entity extraction (medications, conditions, allergies, labs, dates).
2. Plain-language explanation + questions for the doctor.
3. Image description metadata (optional, no findings).
4. Health summaries (existing) with a status banner explaining why AI is off.

## Added later
* Shared emails (report + AI summary) set `Reply-To` to the patient and name them in the body; the visible From stays the configured sender.
* Account export (ZIP) and account deletion, with UI under Settings > Your data.

## Performance
Backend: Argon2, Tesseract, PyMuPDF and disk I/O moved off the event loop;
single hash per signup; emails sent in the background; dashboard counts in
one query; composite indexes; DB pool config; selective gzip; request timing
header + slow-request log.
Frontend: standalone build, `loading.tsx` skeleton, lazy report builder,
package import optimisation, smarter React Query retry/stale times, polling
only while documents are processing.
Docker: bind mounts + `next dev` were the main cause of slowness on Windows;
`docker-compose.prod.yml` now works as the fast local stack.

## Production hardening
Config guard, rate limits (auth/AI/upload), security headers, login
enumeration parity, docs off in production, non-root images, healthchecks,
gunicorn workers, SendGrid/Mailgun providers, stuck-document recovery.

## Verification run in the sandbox
* `pytest`: 192 passed (51 new)
* `ruff check app tests`: clean; `mypy app`: clean (157 files)
* `alembic upgrade head` / downgrade -1 / upgrade / `alembic check`: clean
* Frontend: `eslint` clean, `tsc --noEmit` clean, `next build` OK (standalone output produced)
* `docker compose config` validated for both compose files
Not verified: Docker image builds (no daemon), a live Ollama model.
