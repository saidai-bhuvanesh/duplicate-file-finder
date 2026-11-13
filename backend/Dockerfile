# Multi-stage production Dockerfile for EnterpriseIT-RAG Backend

# --- Stage 1: Build dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
RUN python -c "import tomllib; dependencies = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; open('/tmp/requirements.txt', 'w').write('\n'.join(dependencies))" \
    && pip install --user --no-warn-script-location --no-deps --extra-index-url https://download.pytorch.org/whl/cpu "torch==2.8.0+cpu" \
    && pip install --user --no-warn-script-location -r /tmp/requirements.txt

# --- Stage 2: Final runtime container ---
FROM python:3.11-slim AS runtime

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

COPY --chown=appuser:appuser --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . /app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/ready || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4"]
