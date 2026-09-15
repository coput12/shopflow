import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models, schemas
from .db import engine, get_db, publish_order_event

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    logger.info("orders service started")
    yield


app = FastAPI(
    title="ShopFlow Orders API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url=None,
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "orders"}


@app.get("/readiness")
def readiness() -> dict:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ready"}


@app.get("/api/v1/orders", response_model=list[schemas.OrderOut])
def list_orders(db: Session = Depends(get_db)) -> list[models.Order]:
    return db.query(models.Order).order_by(models.Order.created_at.desc()).all()


@app.post("/api/v1/orders", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(order_in: schemas.OrderIn, db: Session = Depends(get_db)) -> models.Order:
    order = models.Order(product_id=order_in.product_id, quantity=order_in.quantity)
    db.add(order)
    db.commit()
    db.refresh(order)

    try:
        publish_order_event(order.id, order.product_id, order.quantity)
        logger.info("Order %s event published", order.id)
    except Exception:
        logger.exception("Failed to publish order event for %s, retry later", order.id)

    return order