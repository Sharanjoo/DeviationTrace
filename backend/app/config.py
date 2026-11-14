from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://deviationtrace:deviationtrace@localhost:5532/deviationtrace"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    storage_dir: str = "./storage"
    # Encrypts secrets stored in the database (e.g. an organization's AI
    # provider API key). Set a long random value in production; changing it
    # makes previously stored keys unreadable (admins re-enter them).
    secrets_key: str = "dev-secrets-key-change-me"


@lru_cache
def get_settings() -> Settings:
    return Settings()
