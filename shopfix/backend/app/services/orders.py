from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.services import cart as cart_service


def checkout(db: Session, user_id: int) -> Order:
    view = cart_service.cart_view(db, user_id)
    if not view["items"]:
        raise ValueError("Cart is empty")
    order = Order(user_id=user_id, total_cents=view["total_cents"])
    db.add(order)
    db.flush()
    for item in view["items"]:
        db.add(
            OrderItem(
                order_id=order.id,
                listing_id=item["listing_id"],
                quantity=item["quantity"],
                price_cents=item["listing"]["price_cents"],
            )
        )
    cart_service.clear_cart(db, user_id)
    db.commit()
    db.refresh(order)
    return order


def order_to_out(db: Session, order: Order) -> dict:
    items = db.query(OrderItem).filter_by(order_id=order.id).all()
    return {
        "id": order.id,
        "status": order.status,
        "total_cents": order.total_cents,
        "items": [
            {
                "listing_id": i.listing_id,
                "quantity": i.quantity,
                "price_cents": i.price_cents,
            }
            for i in items
        ],
    }
