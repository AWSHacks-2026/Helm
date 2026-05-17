from pydantic import BaseModel


class ListingCreate(BaseModel):
    title: str
    description: str = ""
    price_cents: int
    tags: list[str] = []


class ListingOut(BaseModel):
    id: int
    seller_id: int
    title: str
    description: str
    price_cents: int
    tags: list[str]
