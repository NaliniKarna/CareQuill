FROM python:3.12-slim

WORKDIR /app

# System deps needed by asyncpg / argon2 / reportlab build chains, plus the
# tesseract-ocr binary used by app/ocr/tesseract_engine.py (pytesseract just
# shells out to it). If this package is ever unavailable at build time, the
# app still starts fine -- app/ocr/factory.py falls back to NullOCREngine
# with a warning log rather than crashing.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/storage/medical_documents

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
