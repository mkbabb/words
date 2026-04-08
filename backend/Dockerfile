# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# Runtime dependencies
# - ffmpeg: TTS WAV→MP3 conversion
# - espeak-ng: Kokoro-ONNX phonemization (required for non-English TTS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    espeak-ng \
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
# - curl + ca-certificates + Rust toolchain: for building the ffuzzy wheel
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
       | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy the ffuzzy source via the `ffuzzy` additional build context. The
# pyproject.toml `tool.uv.sources` entry references the path
# `.ffuzzy/crates/ffuzzy-py` (relative to /app/pyproject.toml). uv
# refuses path sources that escape the workspace root, so we vendor the
# crate inside /app under the same name as the local symlink.
COPY --from=ffuzzy . /app/.ffuzzy

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies only (CPU-only PyTorch — no NVIDIA/CUDA packages).
# uv sync will build the ffuzzy wheel via maturin from the path source.
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

# Install development dependencies + the build tools needed to (re)build
# the ffuzzy Rust wheel when uv sync runs from a mounted volume.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
       | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"

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

# Download NLTK data to a shared location accessible by appuser
ENV NLTK_DATA=/usr/share/nltk_data
RUN python -c "import nltk; nltk.download('stopwords', quiet=True, download_dir='/usr/share/nltk_data')"

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