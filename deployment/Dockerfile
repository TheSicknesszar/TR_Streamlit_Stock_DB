# =============================================================================
# RefurbAdmin AI - Production Dockerfile
# =============================================================================
# Multi-stage build for optimized production image
# Based on Python 3.12 slim with security hardening
# POPIA compliant with South African data protection considerations
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
ENV PATH="$POETRY_HOME/bin:$PATH"

# Create working directory
WORKDIR /app

# Copy dependency files
COPY requirements-production.txt .
COPY requirements-dev.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install -r requirements-production.txt

# -----------------------------------------------------------------------------
# Stage 2: Production - Minimal runtime image
# -----------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS production

# Labels
LABEL maintainer="RefurbAdmin AI Team <support@refurbadmin.co.za>"
LABEL version="1.0.0"
LABEL description="RefurbAdmin AI - Inventory and Pricing Management System"
LABEL org.opencontainers.image.source="https://github.com/refurbadmin/pricing_tool_est"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    \
    # Application settings
    APP_HOME="/app" \
    APP_USER="refurbadmin" \
    APP_GROUP="refurbadmin" \
    \
    # Security settings
    VIRTUAL_ENV="/opt/venv" \
    PATH="/opt/venv/bin:$PATH" \
    \
    # Locale settings (South African timezone)
    TZ="Africa/Johannesburg" \
    LANG="en_US.UTF-8" \
    LC_ALL="en_US.UTF-8"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    libpq5 \
    postgresql-client \
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user and group for security
RUN groupadd --gid 1000 ${APP_GROUP} && \
    useradd --uid 1000 --gid ${APP_GROUP} --shell /bin/bash --create-home ${APP_USER}

# Create application directory
WORKDIR ${APP_HOME}

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=${APP_USER}:${APP_GROUP} . .

# Create necessary directories with proper permissions
RUN mkdir -p \
    ${APP_HOME}/logs/audit \
    ${APP_HOME}/logs/app \
    ${APP_HOME}/data/backups \
    ${APP_HOME}/data/cache \
    ${APP_HOME}/data/uploads \
    && chown -R ${APP_USER}:${APP_GROUP} ${APP_HOME}

# Set proper permissions
RUN chmod -R 755 ${APP_HOME} && \
    chmod -R 700 ${APP_HOME}/logs && \
    chmod -R 700 ${APP_HOME}/data

# Switch to non-root user
USER ${APP_USER}

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Entry point with tini for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command - run with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# -----------------------------------------------------------------------------
# Stage 3: Development - With debug tools
# -----------------------------------------------------------------------------
FROM production AS development

USER root

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    vim \
    less \
    netcat-openbsd \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install -r requirements-dev.txt

# Switch back to non-root user
USER ${APP_USER}

# Override command for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
