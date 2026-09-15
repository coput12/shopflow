import json
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session

from . import models, schemas
from .db import engine, get_db, redis_client

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    logger.info("products service started, tables ensured")
    yield
    logger.info("products service stopped")


app = FastAPI(
    title="ShopFlow Products API",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url=None,
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "service": "products"}


@app.get("/api/v1/products", response_model=list[schemas.ProductOut])
def list_products(db: Session = Depends(get_db)) -> list[models.Product]:
    return db.query(models.Product).all()


@app.get("/api/v1/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)) -> models.Product:
    cache_key = f"product:{product_id}"
    cached = redis_client.get(cache_key)
    if cached:
        logger.info("Cache hit for product %s", product_id)
        return schemas.ProductOut.model_validate_json(cached)

    product = db.get(models.Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    redis_client.setex(cache_key, 60, json.dumps(schemas.ProductOut.model_validate(product).model_dump()))
    return product


@app.post("/api/v1/products", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(product_in: schemas.ProductIn, db: Session = Depends(get_db)) -> models.Product:
    product = models.Product(**product_in.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    redis_client.delete(f"product:{product.id}")
    return product


@app.patch("/api/v1/products/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, update: schemas.ProductUpdate, db: Session = Depends(get_db)) -> models.Product:
    product = db.get(models.Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    redis_client.delete(f"product:{product_id}")
    return product


@app.delete("/api/v1/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)) -> None:
    product = db.get(models.Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    db.delete(product)
    db.commit()
    redis_client.delete(f"product:{product_id}")