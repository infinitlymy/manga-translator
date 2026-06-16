import json
from typing import Any
from sqlmodel import Session, select
from app.models.base import Setting
from app.core.db import get_session

class SettingsService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: str, default: Any = None) -> Any:
        stmt = select(Setting).where(Setting.key == key)
        result = self.session.exec(stmt).first()
        if result is None:
            return default
        if result.value_type == "json":
            return json.loads(result.value)
        elif result.value_type == "int":
            return int(result.value)
        elif result.value_type == "float":
            return float(result.value)
        elif result.value_type == "bool":
            return result.value.lower() in ("true", "1", "yes", "on")
        return result.value

    def set(self, key: str, value: Any, category: str = "general") -> Setting:
        stmt = select(Setting).where(Setting.key == key)
        existing = self.session.exec(stmt).first()
        
        if isinstance(value, dict) or isinstance(value, list):
            value_str = json.dumps(value)
            value_type = "json"
        elif isinstance(value, bool):
            value_str = str(value)
            value_type = "bool"
        elif isinstance(value, int):
            value_str = str(value)
            value_type = "int"
        elif isinstance(value, float):
            value_str = str(value)
            value_type = "float"
        else:
            value_str = str(value)
            value_type = "str"

        if existing:
            existing.value = value_str
            existing.value_type = value_type
            existing.category = category
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing
        else:
            setting = Setting(key=key, value=value_str, value_type=value_type, category=category)
            self.session.add(setting)
            self.session.commit()
            self.session.refresh(setting)
            return setting

    def get_all(self, category: str | None = None) -> dict[str, Any]:
        stmt = select(Setting)
        if category:
            stmt = stmt.where(Setting.category == category)
        results = self.session.exec(stmt).all()
        out = {}
        for r in results:
            if r.value_type == "json":
                out[r.key] = json.loads(r.value)
            elif r.value_type == "int":
                out[r.key] = int(r.value)
            elif r.value_type == "float":
                out[r.key] = float(r.value)
            elif r.value_type == "bool":
                out[r.key] = r.value.lower() in ("true", "1", "yes", "on")
            else:
                out[r.key] = r.value
        return out
