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
EXPOSE 5000

# Add healthcheck directly in Dockerfile for Coolify compatibility
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5000/health || exit 1

# Use Gunicorn for production-ready server
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "src.api:app"]