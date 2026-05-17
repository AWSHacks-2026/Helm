from pydantic import BaseModel

from app.schemas.listing import ListingOut


class CartItemCreate(BaseModel):
    listing_id: int
    quantity: int = 1


class CartItemOut(BaseModel):
    id: int
    listing_id: int
    quantity: int
    listing: ListingOut


class CartOut(BaseModel):
    items: list[CartItemOut]
    total_cents: int
