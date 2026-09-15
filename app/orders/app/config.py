from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ORDERS_", env_file=".env", extra="ignore")

    app_name: str = "orders"
    database_url: str = "postgresql://shopflow:shopflow@postgres:5432/shopflow_orders"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    orders_exchange: str = "shopflow.events"
    orders_queue: str = "shopflow.orders"


@lru_cache
def get_settings() -> Settings:
    return Settings()