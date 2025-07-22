# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# Python environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # UV configuration
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_CACHE_DIR=/opt/uv-cache \
    # Application paths
    APP_PATH=/app

# UV installation layer
FROM base AS uv-installer
COPY --from=ghcr.io/astral-sh/uv:0.7.22 /uv /uvx /bin/

# Dependencies layer
FROM base AS dependencies
WORKDIR ${APP_PATH}
COPY --from=uv-installer /bin/uv /bin/uv

# Copy only dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,target=${UV_CACHE_DIR} \
    uv sync --frozen --no-install-project --no-dev

# Builder layer
FROM dependencies AS builder
WORKDIR ${APP_PATH}

# Copy application source
COPY . .

# Install the project itself
RUN --mount=type=cache,target=${UV_CACHE_DIR} \
    uv sync --frozen --no-dev

# Production runtime
FROM base AS runtime
WORKDIR ${APP_PATH}

# Create non-root user
RUN groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser appuser

# Copy only the virtual environment and application
COPY --from=builder --chown=appuser:appuser ${APP_PATH} ${APP_PATH}

# Set the virtual environment in PATH
ENV PATH="${APP_PATH}/.venv/bin:$PATH"

# Switch to non-root user
USER appuser

# Default command (can be overridden)
CMD ["python", "-m", "uvicorn", "src.floridify.main:app", "--host", "0.0.0.0", "--port", "8000"]