from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKER_", env_file=".env", extra="ignore")

    app_name: str = "worker"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    orders_exchange: str = "shopflow.events"
    orders_queue: str = "shopflow.orders"
    routing_key: str = "order.created"
    redis_url: str = "redis://redis:6379/1"
    prefetch_count: int = 10
    retry_delay_seconds: int = 5
    processing_seconds: float = 1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()