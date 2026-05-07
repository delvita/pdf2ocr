### Builder: build wheels to avoid compiling in final image
FROM python:3.9-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels
COPY requirements.txt /wheels/
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r /wheels/requirements.txt


### Runtime: smaller image with only runtime dependencies
FROM python:3.9-slim

# Install runtime OS packages (tesseract, poppler for PDF processing, and minimal libs for Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    tesseract-ocr-ita \
    poppler-utils \
    libjpeg62-turbo \
    zlib1g \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy pre-built wheels from builder and install
COPY --from=builder /wheels /wheels
COPY requirements.txt /app/
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /app/requirements.txt

# Copy application
COPY . /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
# Defaults für lange OCR-Läufe (n8n/Reverse-Proxy separat anpassen)
ENV GUNICORN_TIMEOUT=900
ENV GUNICORN_GRACEFUL_TIMEOUT=900
EXPOSE 5000

# Add healthcheck directly in Dockerfile for Coolify compatibility
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5000/health || exit 1

# Absoluter Config-Pfad + explizite Timeouts (CLI), damit kein stiller 30s-Default greift,
# falls CWD/Startkommando von gunicorn_config.py abweicht. Werte per ENV anpassbar.
CMD ["sh", "-c", "exec gunicorn -c /app/gunicorn_config.py --timeout \"${GUNICORN_TIMEOUT:-900}\" --graceful-timeout \"${GUNICORN_GRACEFUL_TIMEOUT:-900}\" src.api:app"]