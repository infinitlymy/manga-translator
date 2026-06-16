import secrets
from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    APP_NAME: str = "Manga Translator"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'app.db'}"
    
    # Storage
    STORAGE_BACKEND: str = "local"  # local, s3
    STORAGE_LOCAL_PATH: str = str(DATA_DIR / "storage")
    STORAGE_URL_PREFIX: str = "/storage"
    
    # Upload limits
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    MAX_UPLOAD_CHUNK_SIZE: int = 5 * 1024 * 1024  # 5MB chunks
    ALLOWED_IMAGE_TYPES: set[str] = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # Admin (set during setup wizard)
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD_HASH: str | None = None
    SETUP_COMPLETED: bool = False
    
    # ML / Translation defaults
    DEFAULT_DETECTOR: str = "default"
    DEFAULT_TRANSLATOR: str = "youdao"
    DEFAULT_INPAINTER: str = "default"
    DEFAULT_TARGET_LANG: str = "CHS"
    
    # Worker
    WORKER_HOST: str = "127.0.0.1"
    WORKER_PORT: int = 8001
    WORKER_NONCE: str | None = None
    
    # Retention
    RESULT_RETENTION_DAYS: int = 30
    
    # Resource paths (manga_translator engine expects these relative to BASE_PATH)
    DICT_PATH: str = str(DATA_DIR / "dict")
    FONT_PATH: str = str(BASE_DIR / "fonts")
    
    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()
