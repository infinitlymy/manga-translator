# Multi-stage Dockerfile for Manga Translator Webapp
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend runtime
FROM python:3.11-slim AS backend
WORKDIR /app

# Install system dependencies for OpenCV, Pillow, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy backend dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy ML dependencies (PyTorch CPU by default; override for GPU)
COPY backend/requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements-ml.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend static files
COPY --from=frontend-builder /app/frontend/dist ./app/static

# Environment
ENV PYTHONPATH=/app
ENV APP_ENV=production
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
