from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PRODUCTS_", env_file=".env", extra="ignore")

    app_name: str = "products"
    database_url: str = "postgresql://shopflow:shopflow@postgres:5432/shopflow"
    redis_url: str = "redis://redis:6379/0"
    redis_cache_ttl: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()