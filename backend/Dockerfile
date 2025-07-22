# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
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
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies only
RUN --mount=type=cache,target=/opt/uv-cache \
    uv sync --frozen --no-install-project --no-dev

# Builder stage
FROM dependencies AS builder
WORKDIR /app

# Copy source code
COPY . .

# Download and install AWS RDS CA certificate bundle
# This provides TLS certificates for AWS DocumentDB connections
# Place in /opt to avoid volume mount conflicts
RUN curl -o /opt/rds-ca-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem && \
    chmod 644 /opt/rds-ca-bundle.pem

# Install application
RUN --mount=type=cache,target=/opt/uv-cache \
    uv sync --frozen --no-dev

# Development stage
FROM base AS development
WORKDIR /app

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv-installer /bin/uv /bin/uv
COPY --from=builder /app /app

# Copy certificate from builder stage to persistent location outside volume mount
COPY --from=builder /opt/rds-ca-bundle.pem /usr/local/share/rds-ca-bundle.pem
RUN chmod 644 /usr/local/share/rds-ca-bundle.pem

ENV PATH="/app/.venv/bin:$PATH"

# Install with dev dependencies
RUN --mount=type=cache,target=/opt/uv-cache \
    uv sync --frozen

CMD ["uvicorn", "src.floridify.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production
WORKDIR /app

# Create non-root user
RUN groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser appuser

# Copy virtual environment and application
COPY --from=builder --chown=appuser:appuser /app /app

# Set PATH
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Production command with proper worker configuration
CMD ["uvicorn", "src.floridify.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]