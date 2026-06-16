from datetime import datetime, timezone
from typing import Any
from sqlmodel import SQLModel, Field, Column, JSON
import uuid

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def new_uuid() -> str:
    return str(uuid.uuid4())

class TimestampMixin(SQLModel):
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime | None = Field(default=None)

class User(TimestampMixin, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=new_uuid, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="admin")  # admin, user
    is_active: bool = Field(default=True)

class Setting(TimestampMixin, table=True):
    __tablename__ = "settings"
    id: str = Field(default_factory=new_uuid, primary_key=True)
    key: str = Field(index=True, unique=True)
    value: str
    value_type: str = Field(default="str")  # str, int, float, bool, json
    category: str = Field(default="general")  # general, translation, storage, security

class Collection(TimestampMixin, table=True):
    __tablename__ = "collections"
    id: str = Field(default_factory=new_uuid, primary_key=True)
    name: str
    description: str | None = Field(default=None)
    cover_asset_id: str | None = Field(default=None, foreign_key="assets.id")
    sort_order: int = Field(default=0)
    status: str = Field(default="active")  # active, archived, deleted
    series: str | None = Field(default=None, index=True)
    artist: str | None = Field(default=None, index=True)
    config: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))  # per-collection translation settings

class Asset(TimestampMixin, table=True):
    __tablename__ = "assets"
    id: str = Field(default_factory=new_uuid, primary_key=True)
    collection_id: str | None = Field(default=None, foreign_key="collections.id")
    original_name: str
    stored_path: str
    mime_type: str
    size: int
    width: int | None = Field(default=None)
    height: int | None = Field(default=None)
    sort_index: int = Field(default=0)
    status: str = Field(default="uploaded")  # uploaded, processing, completed, error
    sha256: str | None = Field(default=None, index=True)
    meta: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    config: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))  # per-asset translation overrides

class Job(TimestampMixin, table=True):
    __tablename__ = "jobs"
    id: str = Field(default_factory=new_uuid, primary_key=True)
    collection_id: str | None = Field(default=None, foreign_key="collections.id")
    name: str | None = Field(default=None)
    config_snapshot: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = Field(default="pending")  # pending, running, paused, completed, failed, cancelled
    progress: float = Field(default=0.0)  # 0-100
    error_message: str | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

class Task(TimestampMixin, table=True):
    __tablename__ = "tasks"
    id: str = Field(default_factory=new_uuid, primary_key=True)
    job_id: str = Field(foreign_key="jobs.id")
    asset_id: str = Field(foreign_key="assets.id")
    status: str = Field(default="pending")  # pending, running, completed, failed, cancelled
    progress: float = Field(default=0.0)
    error_message: str | None = Field(default=None)
    result_id: str | None = Field(default=None, foreign_key="results.id")
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

class Result(TimestampMixin, table=True):
    __tablename__ = "results"
    id: str = Field(default_factory=new_uuid, primary_key=True)
    asset_id: str = Field(foreign_key="assets.id")
    job_id: str | None = Field(default=None, foreign_key="jobs.id")
    stored_path: str
    thumb_path: str | None = Field(default=None)
    format: str = Field(default="png")
    width: int | None = Field(default=None)
    height: int | None = Field(default=None)

class ExportProfile(TimestampMixin, table=True):
    __tablename__ = "export_profiles"
    id: str = Field(default_factory=new_uuid, primary_key=True)
    name: str
    pattern: str = Field(default="{prefix}{pad}{index}{ext}")
    prefix: str = Field(default="")
    padding: int = Field(default=0)  # 0 = auto
    start_index: int = Field(default=1)
    step: int = Field(default=1)
    grouping: str = Field(default="none")  # none, collection, chapter
    include_originals: bool = Field(default=False)
    include_masks: bool = Field(default=False)
    include_side_by_side: bool = Field(default=False)

class Dictionary(TimestampMixin, table=True):
    __tablename__ = "dictionaries"
    id: str = Field(default_factory=new_uuid, primary_key=True)
    collection_id: str | None = Field(default=None, foreign_key="collections.id", index=True)
    series: str | None = Field(default=None, index=True)  # applies to all collections with this series
    artist: str | None = Field(default=None, index=True)  # applies to all collections with this artist
    pattern: str  # regex or literal pattern to match
    replacement: str  # replacement text (empty = delete)
    phase: str = Field(default="post")  # "pre" = before translation, "post" = after translation
    is_regex: bool = Field(default=False)
    is_global: bool = Field(default=False)  # if true, applies to all collections
    auto_learned: bool = Field(default=False)  # created by background auto-learn
    usage_count: int = Field(default=0)  # how many times this term was applied
    last_used_at: datetime | None = Field(default=None)
    note: str | None = Field(default=None)

class TextRegion(TimestampMixin, table=True):
    __tablename__ = "text_regions"
    id: str = Field(default_factory=new_uuid, primary_key=True)
    job_id: str = Field(foreign_key="jobs.id", index=True)
    asset_id: str = Field(foreign_key="assets.id", index=True)
    collection_id: str | None = Field(default=None, foreign_key="collections.id", index=True)
    source_text: str
    translated_text: str | None = Field(default=None)
    confidence: float | None = Field(default=None)
    bbox: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))  # {x, y, w, h}
    auto_learned: bool = Field(default=False)  # whether this pair became a dictionary entry

class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"
    id: str = Field(default_factory=new_uuid, primary_key=True)
    table_name: str = Field(index=True)  # collections, dictionaries, settings, jobs, etc.
    record_id: str = Field(index=True)
    action: str  # create, update, delete
    user_id: str | None = Field(default=None)
    old_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    new_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    reverted_at: datetime | None = Field(default=None)
    reverted_by: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
