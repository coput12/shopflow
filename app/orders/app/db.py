import pika
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _connect_rabbit() -> pika.BlockingConnection:
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.exchange_declare(exchange=settings.orders_exchange, exchange_type="topic", durable=True)
    return connection, channel


def publish_order_event(order_id: int, product_id: int, quantity: int) -> None:
    import json

    connection, channel = _connect_rabbit()
    try:
        channel.basic_publish(
            exchange=settings.orders_exchange,
            routing_key="order.created",
            body=json.dumps({"order_id": order_id, "product_id": product_id, "quantity": quantity}),
            properties=pika.BasicProperties(delivery_mode=2),
        )
    finally:
        connection.close()