import asyncio
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image
from sqlmodel import Session, select

logger = logging.getLogger(__name__)

# Lazy imports to avoid heavy startup costs
translator_module = None
Config = None
Context = None

def _lazy_import():
    global translator_module, Config, Context
    if translator_module is None:
        from manga_translator import MangaTranslator
        from manga_translator.config import Config as _Config
        from manga_translator.utils.generic import Context as _Context
        translator_module = MangaTranslator
        Config = _Config
        Context = _Context
    return translator_module, Config, Context


class TranslatorWorker:
    """Background worker that consumes pending jobs and processes them via MangaTranslator."""

    def __init__(self, db_engine):
        self.db_engine = db_engine
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self._translator: Any = None
        self._lock = asyncio.Lock()

    def start(self):
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._worker_loop())
            logger.info("Translator worker started")

    async def enqueue(self, job_id: str):
        await self._queue.put(job_id)

    async def _worker_loop(self):
        while True:
            job_id = await self._queue.get()
            try:
                await self._process_job(job_id)
            except Exception as e:
                logger.exception(f"Job {job_id} failed: {e}")
                await self._fail_job(job_id, str(e))
            finally:
                self._queue.task_done()

    def _get_translator(self, use_gpu: bool = False, pre_dict_path: str | None = None, post_dict_path: str | None = None):
        if self._translator is None:
            MangaTranslator, _, _ = _lazy_import()
            params = {
                "use_gpu": use_gpu,
                "batch_size": 1,
                "verbose": False,
                "ignore_errors": True,
                "models_ttl": 0,
            }
            if pre_dict_path:
                params["pre_dict"] = pre_dict_path
            if post_dict_path:
                params["post_dict"] = post_dict_path
            self._translator = MangaTranslator(params)
            logger.info("MangaTranslator initialized")
        return self._translator

    def _build_dict_files(self, session, collection_id: str | None) -> tuple[str | None, str | None]:
        """Query DB for dictionary entries and write temp dict files. Returns (pre_path, post_path)."""
        from app.models.base import Dictionary, Collection
        import tempfile

        pre_entries = []
        post_entries = []

        coll = session.get(Collection, collection_id) if collection_id else None
        if coll and (coll.series or coll.artist):
            stmt = select(Dictionary).where(
                (Dictionary.is_global == True) |
                (Dictionary.collection_id == collection_id) |
                (Dictionary.series == coll.series) |
                (Dictionary.artist == coll.artist)
            )
        else:
            stmt = select(Dictionary).where(
                (Dictionary.is_global == True) |
                (Dictionary.collection_id == collection_id)
            )
        entries = session.exec(stmt).all()

        for entry in entries:
            line = f"{entry.pattern} {entry.replacement}"
            if entry.phase == "pre":
                pre_entries.append(line)
            else:
                post_entries.append(line)

        pre_path = None
        post_path = None

        if pre_entries:
            fd, pre_path = tempfile.mkstemp(suffix="_pre_dict.txt", prefix="dict_", text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for line in pre_entries:
                    f.write(line + "\n")

        if post_entries:
            fd, post_path = tempfile.mkstemp(suffix="_post_dict.txt", prefix="dict_", text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for line in post_entries:
                    f.write(line + "\n")

        return pre_path, post_path

    async def _process_job(self, job_id: str):
        from app.models.base import Job, Task, Asset, Result
        from app.services.storage import get_storage

        with Session(self.db_engine) as session:
            job = session.get(Job, job_id)
            if not job or job.status not in ("pending", "running"):
                return

            tasks = session.exec(select(Task).where(Task.job_id == job_id)).all()
            if not tasks:
                job.status = "completed"
                job.progress = 100.0
                job.completed_at = datetime.utcnow()
                session.add(job)
                session.commit()
                return

            # Build dictionary files for this collection
            pre_dict_path, post_dict_path = self._build_dict_files(session, job.collection_id)

            # Build config from snapshot
            config = self._build_config(job.config_snapshot or {})

            # Update job status
            job.status = "running"
            job.started_at = datetime.utcnow()
            session.add(job)
            session.commit()

        total = len(tasks)
        completed = 0

        try:
            for task in tasks:
                # Re-open session per task to avoid long-lived transactions
                with Session(self.db_engine) as session:
                    task = session.get(Task, task.id)
                    if task.status in ("completed", "cancelled", "failed"):
                        continue

                    asset = session.get(Asset, task.asset_id)
                    if not asset:
                        task.status = "failed"
                        task.error_message = "Asset not found"
                        session.add(task)
                        session.commit()
                        continue

                    try:
                        # Load image from storage
                        storage = get_storage()
                        image_data = await storage.read(asset.stored_path)
                        image = Image.open(io.BytesIO(image_data)).convert("RGB")

                        # Translate with collection-specific dictionaries
                        translator = self._get_translator(
                            use_gpu=(job.config_snapshot or {}).get("use_gpu", False),
                            pre_dict_path=pre_dict_path,
                            post_dict_path=post_dict_path,
                        )
                        ctx = await translator.translate(image, config)

                        if ctx.result is None:
                            raise RuntimeError("Translation produced no result")

                        # Save text regions for auto-learning
                        if hasattr(ctx, "text_regions") and ctx.text_regions:
                            from app.services.auto_learn_service import save_text_regions
                            save_text_regions(
                                session, job.id, asset.id, job.collection_id, ctx.text_regions
                            )

                        # Save result
                        result_filename = f"results/{job.id}/{asset.id}.png"
                        os.makedirs(
                            Path(get_storage().base_path) / "results" / job.id,
                            exist_ok=True,
                        )
                        buf = io.BytesIO()
                        ctx.result.save(buf, format="PNG")
                        buf.seek(0)
                        await storage.save(result_filename, buf.read(), "image/png")

                        # Create result record
                        result = Result(
                            asset_id=asset.id,
                            job_id=job.id,
                            stored_path=result_filename,
                            format="png",
                            width=ctx.result.width,
                            height=ctx.result.height,
                        )
                        session.add(result)

                        task.status = "completed"
                        task.result_id = result.id
                        task.completed_at = datetime.utcnow()
                        session.add(task)
                        session.commit()

                        completed += 1
                    except Exception as e:
                        logger.exception(f"Task {task.id} failed: {e}")
                        task.status = "failed"
                        task.error_message = str(e)[:500]
                        session.add(task)
                        session.commit()

                # Update job progress
                progress = (completed / total) * 100
                with Session(self.db_engine) as session:
                    job = session.get(Job, job_id)
                    job.progress = progress
                    session.add(job)
                    session.commit()
        finally:
            # Clean up temp dict files
            for path in (pre_dict_path, post_dict_path):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

        # Mark job completed or failed
        with Session(self.db_engine) as session:
            job = session.get(Job, job_id)
            failed_tasks = session.exec(
                select(Task).where(Task.job_id == job_id, Task.status == "failed")
            ).all()
            if failed_tasks:
                job.status = "failed" if completed == 0 else "completed"
                job.error_message = f"{len(failed_tasks)} task(s) failed"
            else:
                job.status = "completed"
            job.progress = 100.0
            job.completed_at = datetime.utcnow()
            session.add(job)
            session.commit()

            # Run auto-learn for this collection
            if job.collection_id and job.status == "completed":
                try:
                    from app.services.auto_learn_service import run_auto_learn
                    run_auto_learn(session, job.collection_id, job_id)
                except Exception:
                    logger.exception("Auto-learn failed")

    def _build_config(self, snapshot: dict) -> Any:
        """Build MangaTranslator Config from job config snapshot."""
        _, ConfigCls, _ = _lazy_import()
        # Merge defaults with snapshot
        defaults = {
            "translator": {"translator": "sugoi", "target_lang": "ENG"},
            "detector": {"detector": "default"},
            "inpainter": {"inpainter": "lama_large"},
            "ocr": {"ocr": "ocr48px"},
            "render": {"renderer": "default"},
        }
        merged = {**defaults, **snapshot}
        return ConfigCls(**merged)

    async def _fail_job(self, job_id: str, message: str):
        from app.models.base import Job
        with Session(self.db_engine) as session:
            job = session.get(Job, job_id)
            if job:
                job.status = "failed"
                job.error_message = message
                job.completed_at = datetime.utcnow()
                session.add(job)
                session.commit()

    async def cancel_job(self, job_id: str):
        """Cancel a running job by removing it from queue or marking it."""
        from app.models.base import Job, Task
        with Session(self.db_engine) as session:
            job = session.get(Job, job_id)
            if not job:
                return False
            if job.status == "pending":
                job.status = "cancelled"
                job.completed_at = datetime.utcnow()
                session.add(job)
                # Also mark all tasks as cancelled
                tasks = session.exec(select(Task).where(Task.job_id == job_id)).all()
                for t in tasks:
                    t.status = "cancelled"
                    session.add(t)
                session.commit()
                return True
            # For running jobs, the worker loop checks status before each task
            job.status = "cancelled"
            session.add(job)
            session.commit()
            return True


# Module-level singleton
_worker: TranslatorWorker | None = None


def init_worker(db_engine):
    global _worker
    _worker = TranslatorWorker(db_engine)
    _worker.start()
    return _worker


def get_worker() -> TranslatorWorker:
    if _worker is None:
        raise RuntimeError("Worker not initialized. Call init_worker first.")
    return _worker
