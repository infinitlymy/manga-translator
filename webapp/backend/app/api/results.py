from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select
from app.api.deps import require_admin
from app.core.db import get_session
from app.models.base import Result, Asset, User
from app.services.storage import get_storage, LocalStorage

router = APIRouter(prefix="/results", tags=["results"])

@router.get("/")
def list_results(
    collection_id: str | None = None,
    asset_id: str | None = None,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    stmt = select(Result)
    if collection_id:
        # Need to join via assets
        assets = session.exec(select(Asset).where(Asset.collection_id == collection_id)).all()
        asset_ids = {a.id for a in assets}
        if asset_ids:
            stmt = stmt.where(Result.asset_id.in_(asset_ids))
    if asset_id:
        stmt = stmt.where(Result.asset_id == asset_id)
    stmt = stmt.order_by(Result.created_at.desc())
    return session.exec(stmt).all()

@router.get("/{result_id}")
def get_result(
    result_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    result = session.get(Result, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    return result

@router.get("/{result_id}/image")
async def get_result_image(
    result_id: str,
    thumb: bool = False,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    result = session.get(Result, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    
    storage = get_storage()
    path = result.thumb_path if thumb and result.thumb_path else result.stored_path
    
    if isinstance(storage, LocalStorage):
        local_path = storage.get_local_path(path)
        if not local_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file not found")
        
        async def file_iterator():
            with open(local_path, "rb") as f:
                while chunk := f.read(8192):
                    yield chunk
        
        ext = local_path.suffix.lstrip(".").lower()
        media_type = "image/png" if ext == "png" else "image/jpeg" if ext in ("jpg", "jpeg") else "application/octet-stream"
        return StreamingResponse(file_iterator(), media_type=media_type)
    else:
        data = await storage.read(path)
        return StreamingResponse(iter([data]), media_type="image/png")

@router.delete("/{result_id}")
async def delete_result(
    result_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    result = session.get(Result, result_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")
    
    storage = get_storage()
    await storage.delete(result.stored_path)
    if result.thumb_path:
        await storage.delete(result.thumb_path)
    
    session.delete(result)
    session.commit()
    return {"message": "Result deleted"}
