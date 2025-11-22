# Multi-stage Dockerfile for Python 3.12 development

FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base as development

# Copy dependency files and project structure needed for installation
COPY requirements.txt requirements-dev.txt pyproject.toml README.md ./
COPY src/ ./src/

# Install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements-dev.txt && \
    pip install -e .

# Copy remaining project files
COPY . .

# Default command for development
CMD ["/bin/bash"]

# Production stage
FROM base as production

# Copy dependency files and project structure needed for installation
COPY requirements.txt pyproject.toml README.md ./
COPY src/ ./src/

# Install production dependencies only
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install -e .

# Set default command
CMD ["python", "-m", "src"]

