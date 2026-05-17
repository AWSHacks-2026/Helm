from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps.auth import current_user_id
from app.schemas.order import OrderOut
from app.services import orders as order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/checkout", status_code=201, response_model=OrderOut)
def checkout(db: Session = Depends(get_db), user_id: int = Depends(current_user_id)):
    try:
        order = order_service.checkout(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return order_service.order_to_out(db, order)
