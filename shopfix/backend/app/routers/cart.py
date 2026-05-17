from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps.auth import current_user_id
from app.schemas.cart import CartItemCreate, CartOut
from app.services import cart as cart_service

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartOut)
def get_cart(db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    return cart_service.cart_view(db, user_id)


@router.post("/items", status_code=201)
def add_cart_item(
    payload: CartItemCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(current_user_id),
):
    try:
        cart_service.add_item(db, user_id, payload.listing_id, payload.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"added": True}
