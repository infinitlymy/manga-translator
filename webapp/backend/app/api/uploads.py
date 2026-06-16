import hashlib
import io
import imghdr
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlmodel import Session, select
from PIL import Image
from app.api.deps import get_current_user, require_admin
from app.core.db import get_session
from app.core.config import get_settings
from app.models.base import Asset, Collection, User
from app.services.storage import get_storage
from app.services.audit_log_service import record_change

router = APIRouter(prefix="/uploads", tags=["uploads"])

# Cross-platform MIME detection without python-magic
IMG_EXT_TO_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}

def _detect_mime(data: bytes, filename: str) -> str | None:
    kind = imghdr.what(None, data)
    if kind:
        return IMG_EXT_TO_MIME.get(kind)
    # Fallback to extension
    ext = Path(filename).suffix.lstrip(".").lower()
    return IMG_EXT_TO_MIME.get(ext)

def _validate_image(file: UploadFile, data: bytes) -> tuple[str, int, int | None, int | None]:
    settings = get_settings()
    if len(data) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
    
    mime = _detect_mime(data, file.filename or "")
    if not mime or mime not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported file type")
    
    try:
        img = Image.open(io.BytesIO(data))
        width, height = img.size
    except Exception:
        width, height = None, None
    
    return mime, len(data), width, height

@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    collection_id: str | None = None,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    data = await file.read()
    mime, size, width, height = _validate_image(file, data)
    
    sha256 = hashlib.sha256(data).hexdigest()
    # Deduplication check
    existing = session.exec(select(Asset).where(Asset.sha256 == sha256)).first()
    if existing:
        return {"asset_id": existing.id, "duplicate": True}
    
    ext = Path(file.filename or "unknown").suffix.lstrip(".") or "png"
    stored_path = f"assets/{collection_id or 'default'}/{sha256[:2]}/{sha256}.{ext}"
    
    storage = get_storage()
    await storage.save(stored_path, data, mime)
    
    asset = Asset(
        collection_id=collection_id,
        original_name=file.filename or "unnamed",
        stored_path=stored_path,
        mime_type=mime,
        size=size,
        width=width,
        height=height,
        sha256=sha256
    )
    session.add(asset)
    record_change(
        session, "assets", asset.id, "create", user.id, None,
        {"original_name": asset.original_name, "collection_id": asset.collection_id, "stored_path": asset.stored_path, "mime_type": asset.mime_type, "size": asset.size}
    )
    session.commit()
    session.refresh(asset)
    return {"asset_id": asset.id, "duplicate": False}

@router.get("/assets")
def list_assets(
    collection_id: str | None = None,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    stmt = select(Asset)
    if collection_id:
        stmt = stmt.where(Asset.collection_id == collection_id)
    results = session.exec(stmt).all()
    return results

@router.patch("/assets/{asset_id}")
def update_asset(
    asset_id: str,
    sort_index: int | None = None,
    original_name: str | None = None,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    old_data = {"sort_index": asset.sort_index, "original_name": asset.original_name}
    if sort_index is not None:
        asset.sort_index = sort_index
    if original_name is not None:
        asset.original_name = original_name
    session.add(asset)
    record_change(
        session, "assets", asset.id, "update", user.id, old_data,
        {"sort_index": asset.sort_index, "original_name": asset.original_name}
    )
    session.commit()
    session.refresh(asset)
    return asset

@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    old_data = {"original_name": asset.original_name, "collection_id": asset.collection_id, "stored_path": asset.stored_path, "mime_type": asset.mime_type}
    storage = get_storage()
    await storage.delete(asset.stored_path)
    session.delete(asset)
    record_change(
        session, "assets", asset.id, "delete", user.id, old_data, None
    )
    session.commit()
    return {"message": "Asset deleted"}
