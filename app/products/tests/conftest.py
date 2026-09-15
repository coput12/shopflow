import os

os.environ.setdefault("PRODUCTS_DATABASE_URL", "sqlite:///./test_products.db")
os.environ.setdefault("PRODUCTS_REDIS_URL", "redis://localhost:6379/9")

import pytest
from app.db import engine
from app.models import Base


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()