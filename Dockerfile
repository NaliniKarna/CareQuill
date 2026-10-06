# Multi-stage build.
#   builder    - compiles wheels (needs gcc/libpq-dev); never shipped.
#   production - slim runtime, non-root user, gunicorn + uvicorn workers.
#   dev        - same runtime but runs uvicorn; docker-compose.yml uses this.
#
# Tesseract is installed with English + Hindi + Nepali data so scanned
# prescriptions and reports in those scripts can be read. Add more
# `tesseract-ocr-<lang>` packages and extend OCR_LANGUAGES to taste.

FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime-base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin tesseract-ocr-nep \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels
RUN groupadd --system app && useradd --system --gid app --home /app app
# Entrypoint starts as root only to fix volume ownership, then drops to `app`.
# (CRLF is stripped in case the repo was checked out on Windows.)
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# ---------------------------------------------------------------------------
FROM runtime-base AS dev
COPY --chown=app:app . .
RUN mkdir -p /app/storage/medical_documents && chown -R app:app /app/storage
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------------------------------------------------------------------------
FROM runtime-base AS production
COPY --chown=app:app . .
RUN mkdir -p /app/storage/medical_documents && chown -R app:app /app/storage
EXPOSE 8000
# WEB_CONCURRENCY sets the worker count (default 2). Keep
# (DB_POOL_SIZE + DB_MAX_OVERFLOW) * workers below Postgres' max_connections.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1
CMD ["sh", "-c", "exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 -w ${WEB_CONCURRENCY:-2} --timeout 120 --graceful-timeout 30 --access-logfile - --forwarded-allow-ips='*'"]
