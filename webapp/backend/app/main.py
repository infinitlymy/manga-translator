import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.db import init_db, get_session, engine
from app.core.config import get_settings
from app.api import auth, settings as settings_api, uploads, collections, jobs, results, export, dictionaries, audit_log
from sqlmodel import Session, select
from app.models.base import User
from app.services.translator_worker import init_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    init_worker(engine)
    yield

settings = get_settings()
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    redirect_slashes=True,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Security headers
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if not settings.DEBUG:
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:;"
    return response

# API routers
app.include_router(auth.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(uploads.router, prefix="/api")
app.include_router(collections.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(results.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(dictionaries.router, prefix="/api")
app.include_router(audit_log.router, prefix="/api")

# Health check
@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# Setup status
@app.get("/api/setup-status")
def setup_status(session: Session = Depends(get_session)):
    existing = session.exec(select(User)).first()
    return {"setup_completed": existing is not None}

# Static files for storage
storage_path = Path(settings.STORAGE_LOCAL_PATH)
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")

# Serve SPA build
# The built frontend should be placed in webapp/backend/static
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="spa")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
