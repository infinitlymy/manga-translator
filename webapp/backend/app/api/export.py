import io
import zipfile
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select
from app.api.deps import require_admin
from app.core.db import get_session
from app.models.base import ExportProfile, Result, Asset, Collection, User
from app.services.storage import get_storage, LocalStorage

router = APIRouter(prefix="/export", tags=["export"])

class ExportProfileCreate(BaseModel):
    name: str
    pattern: str = "{prefix}{pad}{index}{ext}"
    prefix: str = ""
    padding: int = 0
    start_index: int = 1
    step: int = 1
    grouping: str = "none"
    include_originals: bool = False
    include_masks: bool = False
    include_side_by_side: bool = False

class ZipExportRequest(BaseModel):
    result_ids: list[str] | None = None
    collection_id: str | None = None
    profile_id: str | None = None
    naming_pattern: str | None = None
    prefix: str = ""
    padding: int = 0
    start_index: int = 1

NATURAL_SORT_RE = re.compile(r"(\d+)")

def natural_sort_key(s: str):
    return [int(text) if text.isdigit() else text.lower() for text in NATURAL_SORT_RE.split(s)]

def auto_padding(count: int) -> int:
    if count < 10:
        return 1
    if count < 100:
        return 2
    if count < 1000:
        return 3
    return len(str(count))

def apply_pattern(pattern: str, index: int, prefix: str, padding: int, original_name: str, collection_name: str = "", ext: str = ".png") -> str:
    pad_str = str(index).zfill(padding)
    name = Path(original_name).stem
    out = pattern
    out = out.replace("{prefix}", prefix)
    out = out.replace("{index}", str(index))
    out = out.replace("{pad}", pad_str)
    out = out.replace("{name}", name)
    out = out.replace("{collection}", collection_name)
    out = out.replace("{ext}", ext)
    return out

@router.post("/zip")
async def export_zip(
    data: ZipExportRequest,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    # Gather results
    if data.result_ids:
        results = [session.get(Result, rid) for rid in data.result_ids]
        results = [r for r in results if r]
    elif data.collection_id:
        assets = session.exec(select(Asset).where(Asset.collection_id == data.collection_id)).all()
        asset_ids = {a.id for a in assets}
        if asset_ids:
            results = session.exec(select(Result).where(Result.asset_id.in_(asset_ids))).all()
        else:
            results = []
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide result_ids or collection_id")
    
    if not results:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No results found")
    
    # Resolve naming
    profile = None
    if data.profile_id:
        profile = session.get(ExportProfile, data.profile_id)
    
    pattern = data.naming_pattern or (profile.pattern if profile else "{pad}{index}{ext}")
    prefix = data.prefix if data.prefix else (profile.prefix if profile else "")
    padding = data.padding or (profile.padding if profile and profile.padding else auto_padding(len(results)))
    start = data.start_index or (profile.start_index if profile else 1)
    
    storage = get_storage()
    
    # Sort results by original asset name (natural sort)
    result_assets = []
    for r in results:
        asset = session.get(Asset, r.asset_id)
        result_assets.append((r, asset))
    result_assets.sort(key=lambda x: natural_sort_key(x[1].original_name if x[1] else ""))
    
    # Stream zip
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, (result, asset) in enumerate(result_assets):
            idx = start + i
            ext = Path(result.stored_path).suffix or ".png"
            filename = apply_pattern(
                pattern, idx, prefix, padding,
                asset.original_name if asset else f"image_{i}",
                collection_name="",
                ext=ext
            )
            
            if isinstance(storage, LocalStorage):
                local_path = storage.get_local_path(result.stored_path)
                zf.write(local_path, arcname=filename)
            else:
                data_bytes = await storage.read(result.stored_path)
                zf.writestr(filename, data_bytes)
    
    stream.seek(0)
    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=export.zip"}
    )

@router.get("/profiles")
def list_profiles(
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    return session.exec(select(ExportProfile)).all()

@router.post("/profiles")
def create_profile(
    data: ExportProfileCreate,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    profile = ExportProfile(**data.model_dump())
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile
