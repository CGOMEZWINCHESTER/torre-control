from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Torre Control"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/torre_control"
    session_secret: str = "cambia-esta-clave-en-produccion"
    session_cookie_name: str = "torre_session"
    session_max_age: int = 2592000
    secure_cookies: bool = False
    pin_rounds: int = 10
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_pool_class: str = "queue"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
