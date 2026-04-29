from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "ODMS - Online Document Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://odms:odms123@localhost:5432/odms"
    DATABASE_URL_SYNC: str = "postgresql://odms:odms123@localhost:5432/odms"

    REDIS_URL: str = "redis://localhost:6379/0"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_PUBLIC_ENDPOINT: str = "localhost:9000"  # Browser-accessible address (server IP)
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "odms-documents"
    MINIO_SECURE: bool = False

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # ── AI / RAG ────────────────────────────────────────────────
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_MAX_TOKENS: int = 4096
    EMBEDDING_MODEL: str = "BAAI/bge-small-zh-v1.5"
    EMBEDDING_DIM: int = 768
    RAG_TOP_K: int = 5
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50

    # ── SMTP / Email ─────────────────────────────────────────────
    SMTP_HOST: str = "smtp.126.com"
    SMTP_PORT: int = 25
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_ADDR: str = ""
    SMTP_FROM_NAME: str = "ODMS 文档管理系统"
    SMTP_USE_TLS: bool = True

    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    LIBREOFFICE_PATH: str = "/usr/bin/soffice"
    PREVIEW_CACHE_DAYS: int = 30
    EDIT_LOCK_TIMEOUT_HOURS: int = 24

    UPLOAD_CHUNK_SIZE: int = 5 * 1024 * 1024  # 5MB
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
