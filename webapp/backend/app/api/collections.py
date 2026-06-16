from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from app.api.deps import require_admin
from app.core.db import get_session
from app.models.base import Collection, Asset, User
from app.services.audit_log_service import record_change

router = APIRouter(prefix="/collections", tags=["collections"])

class CollectionCreate(BaseModel):
    name: str
    description: str | None = None
    series: str | None = None
    artist: str | None = None

class CollectionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    cover_asset_id: str | None = None
    sort_order: int | None = None
    series: str | None = None
    artist: str | None = None

@router.post("/")
def create_collection(
    data: CollectionCreate,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    coll = Collection(
        name=data.name,
        description=data.description,
        series=data.series,
        artist=data.artist,
    )
    session.add(coll)
    record_change(
        session, "collections", coll.id, "create", user.id, None,
        {"name": coll.name, "description": coll.description, "series": coll.series, "artist": coll.artist, "status": coll.status}
    )
    session.commit()
    session.refresh(coll)
    return coll

@router.get("/")
def list_collections(
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    stmt = select(Collection).where(Collection.status == "active").order_by(Collection.sort_order)
    return session.exec(stmt).all()

@router.get("/{collection_id}")
def get_collection(
    collection_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    coll = session.get(Collection, collection_id)
    if not coll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return coll

@router.get("/{collection_id}/assets")
def get_collection_assets(
    collection_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    stmt = select(Asset).where(Asset.collection_id == collection_id).order_by(Asset.sort_index)
    return session.exec(stmt).all()

@router.put("/{collection_id}")
def update_collection(
    collection_id: str,
    data: CollectionUpdate,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    coll = session.get(Collection, collection_id)
    if not coll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    old_data = {"name": coll.name, "description": coll.description, "series": coll.series, "artist": coll.artist, "cover_asset_id": coll.cover_asset_id, "sort_order": coll.sort_order}
    if data.name is not None:
        coll.name = data.name
    if data.description is not None:
        coll.description = data.description
    if data.cover_asset_id is not None:
        coll.cover_asset_id = data.cover_asset_id
    if data.sort_order is not None:
        coll.sort_order = data.sort_order
    if data.series is not None:
        coll.series = data.series
    if data.artist is not None:
        coll.artist = data.artist
    session.add(coll)
    record_change(
        session, "collections", coll.id, "update", user.id, old_data,
        {"name": coll.name, "description": coll.description, "series": coll.series, "artist": coll.artist, "cover_asset_id": coll.cover_asset_id, "sort_order": coll.sort_order}
    )
    session.commit()
    session.refresh(coll)
    return coll

@router.delete("/{collection_id}")
def delete_collection(
    collection_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    coll = session.get(Collection, collection_id)
    if not coll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    old_data = {"name": coll.name, "description": coll.description, "series": coll.series, "artist": coll.artist, "status": coll.status}
    coll.status = "deleted"
    session.add(coll)
    record_change(
        session, "collections", coll.id, "delete", user.id, old_data, None
    )
    session.commit()
    return {"message": "Collection deleted"}

@router.get("/{collection_id}/config")
def get_collection_config(
    collection_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    coll = session.get(Collection, collection_id)
    if not coll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    return coll.config or {}

@router.put("/{collection_id}/config")
def update_collection_config(
    collection_id: str,
    data: dict[str, Any],
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    coll = session.get(Collection, collection_id)
    if not coll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    old_config = coll.config or {}
    coll.config = data
    session.add(coll)
    record_change(
        session, "collections", coll.id, "update", user.id, {"config": old_config}, {"config": coll.config}
    )
    session.commit()
    session.refresh(coll)
    return coll.config or {}

@router.post("/{collection_id}/assets/{asset_id}")
def add_asset_to_collection(
    collection_id: str,
    asset_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    asset = session.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    old_collection_id = asset.collection_id
    asset.collection_id = collection_id
    session.add(asset)
    record_change(
        session, "assets", asset.id, "update", user.id,
        {"collection_id": old_collection_id}, {"collection_id": asset.collection_id}
    )
    session.commit()
    session.refresh(asset)
    return asset
