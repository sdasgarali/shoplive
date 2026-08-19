"""Orders: buyer order history, seller order queue, and status updates.

Orders are created by checkout (cart.py) and by the buy-now endpoint
(listings.py). This router is read/manage-side only.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import Order, OrderItem, User
from ..security import get_current_user, require_seller

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderItemOut(BaseModel):
    listing_id: int
    title: str
    price: float
    qty: int


class OrderOut(BaseModel):
    id: int
    buyer_id: int
    seller_id: int
    status: str
    total: float
    items: list[OrderItemOut] = []


class OrderStatusUpdate(BaseModel):
    status: str


_ALLOWED_TRANSITIONS = {
    "pending": {"paid", "cancelled"},
    "paid": {"shipped", "cancelled"},
    "shipped": {"cancelled"},
    "cancelled": set(),
}


def _to_out(order: Order, items: list[OrderItem]) -> OrderOut:
    return OrderOut(
        id=order.id,
        buyer_id=order.buyer_id,
        seller_id=order.seller_id,
        status=order.status.value if hasattr(order.status, "value") else str(order.status),
        total=order.total,
        items=[
            OrderItemOut(listing_id=i.listing_id, title=i.title, price=i.price, qty=i.qty)
            for i in items
        ],
    )


@router.get("", response_model=list[OrderOut])
def my_orders(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[OrderOut]:
    orders = session.exec(
        select(Order).where(Order.buyer_id == user.id).order_by(Order.created_at.desc())
    ).all()
    return [_to_out(o, _items(session, o.id)) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> OrderOut:
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.buyer_id != user.id and order.seller_id != user.id:
        raise HTTPException(status_code=403, detail="Not your order")
    return _to_out(order, _items(session, order.id))


@router.get("/seller/queue", response_model=list[OrderOut])
def seller_orders(
    seller: User = Depends(require_seller),
    session: Session = Depends(get_session),
) -> list[OrderOut]:
    orders = session.exec(
        select(Order).where(Order.seller_id == seller.id).order_by(Order.created_at.desc())
    ).all()
    return [_to_out(o, _items(session, o.id)) for o in orders]


@router.patch("/{order_id}/status", response_model=OrderOut)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    seller: User = Depends(require_seller),
    session: Session = Depends(get_session),
) -> OrderOut:
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.seller_id != seller.id:
        raise HTTPException(status_code=403, detail="Only the seller can update this order")

    current = order.status.value if hasattr(order.status, "value") else str(order.status)
    new = payload.status
    if new not in _ALLOWED_TRANSITIONS.get(current, set()):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition {current} -> {new}",
        )
    order.status = new
    session.add(order)
    session.commit()
    session.refresh(order)
    return _to_out(order, _items(session, order.id))


def _items(session: Session, order_id: int) -> list[OrderItem]:
    return session.exec(select(OrderItem).where(OrderItem.order_id == order_id)).all()
