import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Distributed Job Scheduler"
    VERSION: str = "1.0.0"
    API_V1_STR: str = ""

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/job_scheduler"
    )

    # Security & JWT
    JWT_SECRET: str = os.getenv(
        "JWT_SECRET",
        "supersecretjwtkey_change_in_production_min32chars"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]

    # Worker defaults
    WORKER_NAME: str = "worker-default"
    WORKER_CONCURRENCY: int = 5
    POLL_INTERVAL_SECONDS: float = 1.0
    HEARTBEAT_INTERVAL_SECONDS: float = 5.0
    STALE_WORKER_TIMEOUT_SECONDS: float = 15.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
