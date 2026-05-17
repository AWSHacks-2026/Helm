from sqlalchemy.orm import Session

from app.models.listing import Listing


def create_listing(
    db: Session,
    seller_id: int,
    title: str,
    description: str,
    price_cents: int,
    tags: list[str],
) -> Listing:
    listing = Listing(
        seller_id=seller_id,
        title=title,
        description=description,
        price_cents=price_cents,
        tags=",".join(tags),
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def get_listing(db: Session, listing_id: int) -> Listing | None:
    return db.query(Listing).filter_by(id=listing_id).first()


def search_listings(db: Session, q: str | None) -> list[Listing]:
    query = db.query(Listing)
    if q:
        like = f"%{q.lower()}%"
        query = query.filter(Listing.title.ilike(like) | Listing.description.ilike(like))
    return query.order_by(Listing.id.desc()).limit(50).all()


def listing_to_out(listing: Listing) -> dict:
    return {
        "id": listing.id,
        "seller_id": listing.seller_id,
        "title": listing.title,
        "description": listing.description,
        "price_cents": listing.price_cents,
        "tags": [t for t in listing.tags.split(",") if t],
    }
