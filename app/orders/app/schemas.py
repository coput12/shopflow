from pydantic import BaseModel, Field


class OrderIn(BaseModel):
    product_id: int
    quantity: int = Field(ge=1, le=100)


class OrderOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    status: str

    model_config = {"from_attributes": True}