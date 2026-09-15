import os

os.environ.setdefault("ORDERS_DATABASE_URL", "sqlite:///./test_orders.db")
os.environ.setdefault("ORDERS_RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

import pytest
from app.db import engine
from app.models import Base


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()