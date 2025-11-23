# Multi-stage Dockerfile for Odin v2.0.0 with React micro-frontends

# ============================================================================
# Stage 1: Node.js build stage for React applications
# ============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files for dependency installation
COPY package.json package-lock.json* ./
COPY frontend/package.json frontend/package-lock.json* ./frontend/ 2>/dev/null || true
COPY frontend/portal/package.json ./frontend/portal/ 2>/dev/null || true
COPY frontend/packages/shared/package.json ./frontend/packages/shared/ 2>/dev/null || true
COPY frontend/microservices/health/package.json ./frontend/microservices/health/ 2>/dev/null || true

# Install all frontend dependencies
RUN npm install || true

# Copy frontend source code
COPY frontend/ ./

# Build all frontend applications
RUN npm run build:all 2>/dev/null || echo "Frontend build skipped (source not available)"

# ============================================================================
# Stage 2: Python base stage
# ============================================================================
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

# ============================================================================
# Stage 3: Development stage (with hot reload support)
# ============================================================================
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

# Copy compiled frontend from builder stage (if available)
COPY --from=frontend-builder /app/frontend/portal/dist ./frontend/portal/dist 2>/dev/null || true
COPY --from=frontend-builder /app/frontend/microservices/health/dist ./frontend/microservices/health/dist 2>/dev/null || true

# Default command for development
CMD ["/bin/bash"]

# ============================================================================
# Stage 4: Production stage (optimized)
# ============================================================================
FROM base as production

# Copy dependency files and project structure needed for installation
COPY requirements.txt pyproject.toml README.md ./
COPY src/ ./src/

# Install production dependencies only
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install -e .

# Copy compiled frontend from builder stage
COPY --from=frontend-builder /app/frontend/portal/dist ./frontend/portal/dist
COPY --from=frontend-builder /app/frontend/microservices/health/dist ./frontend/microservices/health/dist
COPY --from=frontend-builder /app/frontend/microservices/*/dist ./frontend/microservices/

# Set default command
CMD ["python", "-m", "src"]

