from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select
from app.api.deps import require_admin
from app.core.db import get_session
from app.models.base import Dictionary, Collection, User
from app.services.audit_log_service import record_change

router = APIRouter(prefix="/dictionaries", tags=["dictionaries"])

class DictionaryCreate(BaseModel):
    collection_id: str | None = None
    series: str | None = None
    artist: str | None = None
    pattern: str
    replacement: str = ""
    phase: str = "post"  # "pre" or "post"
    is_regex: bool = False
    is_global: bool = False
    note: str | None = None

class DictionaryUpdate(BaseModel):
    pattern: str | None = None
    replacement: str | None = None
    phase: str | None = None
    is_regex: bool | None = None
    is_global: bool | None = None
    series: str | None = None
    artist: str | None = None
    note: str | None = None

@router.get("/")
def list_dictionaries(
    collection_id: str | None = None,
    series: str | None = None,
    artist: str | None = None,
    phase: str | None = None,
    is_global: bool | None = None,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    stmt = select(Dictionary)
    if collection_id:
        coll = session.get(Collection, collection_id)
        if coll:
            # Match entries scoped to this collection, its series, its artist, or global
            stmt = stmt.where(
                (Dictionary.collection_id == collection_id) |
                (Dictionary.series == coll.series) |
                (Dictionary.artist == coll.artist) |
                (Dictionary.is_global == True)
            )
        else:
            stmt = stmt.where(Dictionary.collection_id == collection_id)
    if series:
        stmt = stmt.where(Dictionary.series == series)
    if artist:
        stmt = stmt.where(Dictionary.artist == artist)
    if phase:
        stmt = stmt.where(Dictionary.phase == phase)
    if is_global is not None:
        stmt = stmt.where(Dictionary.is_global == is_global)
    stmt = stmt.order_by(Dictionary.pattern)
    return session.exec(stmt).all()

@router.post("/")
def create_dictionary(
    data: DictionaryCreate,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    if data.collection_id:
        coll = session.get(Collection, data.collection_id)
        if not coll:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")
    term = Dictionary(
        collection_id=data.collection_id,
        series=data.series,
        artist=data.artist,
        pattern=data.pattern,
        replacement=data.replacement,
        phase=data.phase,
        is_regex=data.is_regex,
        is_global=data.is_global,
        note=data.note,
    )
    session.add(term)
    record_change(
        session, "dictionaries", term.id, "create", user.id, None,
        {"pattern": term.pattern, "replacement": term.replacement, "phase": term.phase, "collection_id": term.collection_id, "series": term.series, "artist": term.artist}
    )
    session.commit()
    session.refresh(term)
    return term

@router.get("/{term_id}")
def get_dictionary(
    term_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    term = session.get(Dictionary, term_id)
    if not term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found")
    return term

@router.put("/{term_id}")
def update_dictionary(
    term_id: str,
    data: DictionaryUpdate,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    term = session.get(Dictionary, term_id)
    if not term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found")
    old_data = {"pattern": term.pattern, "replacement": term.replacement, "phase": term.phase, "collection_id": term.collection_id, "series": term.series, "artist": term.artist, "is_global": term.is_global, "note": term.note}
    if data.pattern is not None:
        term.pattern = data.pattern
    if data.replacement is not None:
        term.replacement = data.replacement
    if data.phase is not None:
        term.phase = data.phase
    if data.is_regex is not None:
        term.is_regex = data.is_regex
    if data.is_global is not None:
        term.is_global = data.is_global
    if data.series is not None:
        term.series = data.series
    if data.artist is not None:
        term.artist = data.artist
    if data.note is not None:
        term.note = data.note
    session.add(term)
    record_change(
        session, "dictionaries", term.id, "update", user.id, old_data,
        {"pattern": term.pattern, "replacement": term.replacement, "phase": term.phase, "collection_id": term.collection_id, "series": term.series, "artist": term.artist, "is_global": term.is_global, "note": term.note}
    )
    session.commit()
    session.refresh(term)
    return term

@router.delete("/{term_id}")
def delete_dictionary(
    term_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    term = session.get(Dictionary, term_id)
    if not term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found")
    old_data = {"pattern": term.pattern, "replacement": term.replacement, "phase": term.phase, "collection_id": term.collection_id, "series": term.series, "artist": term.artist}
    session.delete(term)
    record_change(
        session, "dictionaries", term.id, "delete", user.id, old_data, None
    )
    session.commit()
    return {"message": "Term deleted"}

@router.post("/{term_id}/increment-usage")
def increment_usage(
    term_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    from datetime import datetime, timezone
    term = session.get(Dictionary, term_id)
    if not term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found")
    term.usage_count += 1
    term.last_used_at = datetime.now(timezone.utc)
    session.add(term)
    session.commit()
    session.refresh(term)
    return term
