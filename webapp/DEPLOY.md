# Deployment Guide

## Quick Start (Docker CPU)

```bash
cd webapp
docker compose up --build
```

Access at `http://localhost:8000`

## GPU Deployment

Requires NVIDIA Container Toolkit:

```bash
cd webapp
docker compose -f docker-compose.gpu.yml up --build
```

## Manual Deployment (No Docker)

### Backend
```bash
cd webapp/backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-ml.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend (build once)
```bash
cd webapp/frontend
npm ci
npm run build
```

The build output is served by FastAPI from `backend/app/static/`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `production` | production / development |
| `DATABASE_URL` | `sqlite:///app/data/app.db` | SQL database URL |
| `STORAGE_PATH` | `/app/data/storage` | File storage path |
| `WORKER_THREADS` | `4` | Translation worker threads |
| `CUDA_VISIBLE_DEVICES` | `0` | GPU device ID |

## Persistent Data

Mount these volumes for persistence:
- `./data` — SQLite DB + uploaded files
- `./models` — Downloaded ML models (cache)
