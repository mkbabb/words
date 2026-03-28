# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# Runtime dependencies
# - ffmpeg: TTS WAV→MP3 conversion
# - espeak-ng: Kokoro-ONNX phonemization (required for non-English TTS)
# - libicu-dev: ICU C++ library for PyICU (phonetic transliteration)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    espeak-ng \
    libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# Python environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_CACHE_DIR=/opt/uv-cache

# UV installation
FROM base AS uv-installer
COPY --from=ghcr.io/astral-sh/uv:0.7.22 /uv /uvx /bin/

# Dependencies stage
FROM base AS dependencies
WORKDIR /app
COPY --from=uv-installer /bin/uv /bin/uv

# Install system dependencies for building
# - build-essential: C/C++ compiler for native extensions
# - pkg-config: required by PyICU's setup.py to find ICU
# - libicu-dev: ICU headers + libraries for PyICU compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies only (CPU-only PyTorch — no NVIDIA/CUDA packages)
RUN --mount=type=cache,target=/opt/uv-cache \
    UV_TORCH_BACKEND=cpu uv sync --frozen --no-install-project --no-dev

# Builder stage
FROM dependencies AS builder
WORKDIR /app

# Copy source code
COPY . .

# Install application
RUN --mount=type=cache,target=/opt/uv-cache \
    UV_TORCH_BACKEND=cpu uv sync --frozen --no-dev

# Development stage
FROM base AS development
WORKDIR /app

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv-installer /bin/uv /bin/uv
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Install with dev dependencies
RUN --mount=type=cache,target=/opt/uv-cache \
    uv sync --frozen

# Download NLTK data required by text.constants
RUN python -c "import nltk; nltk.download('stopwords', quiet=True)"

CMD ["uvicorn", "floridify.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production
WORKDIR /app

# Create non-root user
RUN groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser appuser

# Copy virtual environment and application
COPY --from=builder --chown=appuser:appuser /app /app

# Create writable directories for appuser (logs, cache, data for TTS models)
RUN mkdir -p /app/logs /app/cache /app/data && chown -R appuser:appuser /app/logs /app/cache /app/data

# Set PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Download NLTK data required by text.constants (must be before USER appuser)
RUN python -c "import nltk; nltk.download('stopwords', quiet=True)"

# Switch to non-root user
USER appuser

# Health check — generous start-period for model loading (sentence-transformers, FAISS, corpus)
HEALTHCHECK --interval=30s --timeout=15s --start-period=300s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Production command with proper worker configuration
CMD ["uvicorn", "floridify.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "127.0.0.1,172.16.0.0/12,10.0.0.0/8"]