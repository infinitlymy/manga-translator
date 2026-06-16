import asyncio
import json
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from app.api.deps import require_admin
from app.core.db import get_session
from app.models.base import Job, Task, Asset, Result, User, Collection
from app.services.storage import get_storage
from app.services.translator_worker import get_worker
from app.services.audit_log_service import record_change

router = APIRouter(prefix="/jobs", tags=["jobs"])

class JobCreate(BaseModel):
    collection_id: str | None = None
    asset_ids: list[str] | None = None
    name: str | None = None
    config_snapshot: dict[str, Any] = {}

def _merge_configs(base: dict, override: dict | None) -> dict:
    merged = dict(base)
    if override:
        merged.update(override)
    return merged

@router.post("/")
async def create_job(
    data: JobCreate,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    # Build merged config: defaults <- collection config <- asset configs <- request config
    merged_config = dict(data.config_snapshot)

    if data.collection_id:
        coll = session.get(Collection, data.collection_id)
        if coll and coll.config:
            merged_config = _merge_configs(coll.config, merged_config)

    if data.asset_ids:
        for asset_id in data.asset_ids:
            asset = session.get(Asset, asset_id)
            if asset and asset.config:
                merged_config = _merge_configs(asset.config, merged_config)

    job = Job(
        collection_id=data.collection_id,
        name=data.name or f"Job {datetime.now(timezone.utc).isoformat()}",
        config_snapshot=merged_config,
        status="pending"
    )
    session.add(job)
    record_change(
        session, "jobs", job.id, "create", user.id, None,
        {"collection_id": job.collection_id, "name": job.name, "status": job.status, "config_snapshot": job.config_snapshot}
    )
    session.commit()
    session.refresh(job)

    # Create tasks
    if data.asset_ids:
        for i, asset_id in enumerate(data.asset_ids):
            task = Task(job_id=job.id, asset_id=asset_id)
            session.add(task)
    elif data.collection_id:
        assets = session.exec(select(Asset).where(Asset.collection_id == data.collection_id)).all()
        for asset in assets:
            task = Task(job_id=job.id, asset_id=asset.id)
            session.add(task)

    session.commit()

    # Enqueue for processing
    try:
        await get_worker().enqueue(job.id)
    except Exception:
        pass  # Worker may not be initialized yet; job stays pending

    return {
        "id": job.id,
        "collection_id": job.collection_id,
        "name": job.name,
        "status": job.status,
        "progress": job.progress,
        "config_snapshot": job.config_snapshot,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }

@router.get("/")
def list_jobs(
    status: str | None = None,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    stmt = select(Job)
    if status:
        stmt = stmt.where(Job.status == status)
    stmt = stmt.order_by(Job.created_at.desc())
    return session.exec(stmt).all()

@router.get("/{job_id}")
def get_job(
    job_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    tasks = session.exec(select(Task).where(Task.job_id == job_id)).all()
    return {"job": job, "tasks": tasks}

@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status not in ("pending", "running", "paused"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job cannot be cancelled")

    old_status = job.status
    try:
        await get_worker().cancel_job(job_id)
    except Exception:
        # Fallback to DB-only cancellation if worker unavailable
        job.status = "cancelled"
        session.add(job)
        tasks = session.exec(select(Task).where(Task.job_id == job_id)).all()
        for t in tasks:
            t.status = "cancelled"
            session.add(t)
        session.commit()

    record_change(
        session, "jobs", job.id, "update", user.id,
        {"status": old_status}, {"status": "cancelled"}
    )
    session.commit()
    return {"message": "Job cancelled"}

@router.post("/{job_id}/retry")
async def retry_job(
    job_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status not in ("failed", "cancelled"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only failed or cancelled jobs can be retried")

    old_status = job.status
    job.status = "pending"
    job.progress = 0.0
    job.error_message = None
    session.add(job)

    # Reset failed tasks
    tasks = session.exec(select(Task).where(Task.job_id == job_id)).all()
    for task in tasks:
        if task.status in ("failed", "cancelled"):
            task.status = "pending"
            task.progress = 0.0
            task.error_message = None
            session.add(task)

    record_change(
        session, "jobs", job.id, "update", user.id,
        {"status": old_status}, {"status": "pending"}
    )
    session.commit()

    # Re-enqueue
    try:
        await get_worker().enqueue(job_id)
    except Exception:
        pass

    return {"message": "Job retried"}
