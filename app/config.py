from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "postgresql://user:password@localhost:5432/slicer_api"
    API_ENV: str = "development"
    SECRET_KEY: str = "change-me"
    MAX_FILE_SIZE_MB: int = 50
    PRUSASLICER_PATH: str = "/usr/bin/prusa-slicer"
    DEFAULT_MACHINE_RATE_PER_HOUR: float = 1.50
    DEFAULT_MARKUP_MULTIPLIER: float = 1.5
    APP_VERSION: str = "1.0.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
