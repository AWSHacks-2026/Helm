from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps.auth import current_user_id
from app.schemas.listing import ListingCreate, ListingOut
from app.services import listings as listing_service

router = APIRouter(prefix="/listings", tags=["listings"])


@router.post("", status_code=201, response_model=ListingOut)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(current_user_id),
):
    listing = listing_service.create_listing(
        db, user_id, payload.title, payload.description, payload.price_cents, payload.tags
    )
    return listing_service.listing_to_out(listing)


@router.get("", response_model=list[ListingOut])
def list_listings(q: str | None = None, db: Session = Depends(get_db)):
    return [listing_service.listing_to_out(x) for x in listing_service.search_listings(db, q)]


@router.get("/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = listing_service.get_listing(db, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Not found")
    return listing_service.listing_to_out(listing)
