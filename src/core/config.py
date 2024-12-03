from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Directories
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    LOGS_DIR: Path = BASE_DIR / "logs"
    LOGS_DIR.mkdir(exist_ok=True)
    TEMP_DIR: Path = BASE_DIR / "temp"
    TEMP_DIR.mkdir(exist_ok=True)

    # Cors
    CORS_ORIGINS: list[str] = []
    CORS_METHODS: list[str] = []
    CORS_HEADERS: list[str] = []

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_JOBS_DB: int = 0
    REDIS_DATA_LIFETIME: int = 60 * 60 * 24  # 1 day


config = Settings()
