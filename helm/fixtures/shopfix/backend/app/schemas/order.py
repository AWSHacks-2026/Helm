from pydantic import BaseModel


class OrderItemOut(BaseModel):
    listing_id: int
    quantity: int
    price_cents: int


class OrderOut(BaseModel):
    id: int
    status: str
    total_cents: int
    items: list[OrderItemOut]
