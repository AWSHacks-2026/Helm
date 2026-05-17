from sqlalchemy.orm import Session

from app.models.cart import Cart, CartItem
from app.models.listing import Listing
from app.services.listings import get_listing, listing_to_out


def get_or_create_cart(db: Session, user_id: int) -> Cart:
    cart = db.query(Cart).filter_by(user_id=user_id).first()
    if cart:
        return cart
    cart = Cart(user_id=user_id)
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart


def add_item(db: Session, user_id: int, listing_id: int, quantity: int) -> CartItem:
    listing = get_listing(db, listing_id)
    if not listing:
        raise ValueError("Listing not found")
    cart = get_or_create_cart(db, user_id)
    item = db.query(CartItem).filter_by(cart_id=cart.id, listing_id=listing_id).first()
    if item:
        item.quantity += quantity
    else:
        item = CartItem(cart_id=cart.id, listing_id=listing_id, quantity=quantity)
        db.add(item)
    db.commit()
    db.refresh(item)
    return item


def cart_view(db: Session, user_id: int) -> dict:
    cart = get_or_create_cart(db, user_id)
    items = db.query(CartItem).filter_by(cart_id=cart.id).all()
    out_items = []
    total = 0
    for item in items:
        listing = db.query(Listing).filter_by(id=item.listing_id).one()
        total += listing.price_cents * item.quantity
        out_items.append(
            {
                "id": item.id,
                "listing_id": item.listing_id,
                "quantity": item.quantity,
                "listing": listing_to_out(listing),
            }
        )
    return {"items": out_items, "total_cents": total}


def clear_cart(db: Session, user_id: int) -> None:
    cart = get_or_create_cart(db, user_id)
    db.query(CartItem).filter_by(cart_id=cart.id).delete()
    db.commit()
