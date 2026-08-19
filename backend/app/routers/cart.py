"""Cart: add/update/remove buy-now items, view cart, and checkout.

Checkout consumes the cart and creates an Order (+ OrderItems) — the
cart -> checkout -> orders flow. Auction wins are integrated at the
realtime layer and added to the cart via the same add endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ..db import get_session
from ..models import CartItem, Listing, Order, OrderItem, User
from ..security import get_current_user

router = APIRouter(prefix="/cart", tags=["cart"])


class CartAddRequest(BaseModel):
    listing_id: int
    qty: int = Field(default=1, ge=1, le=99)


class CartUpdateRequest(BaseModel):
    qty: int = Field(ge=1, le=99)


class CartItemOut(BaseModel):
    listing_id: int
    title: str
    price: float
    qty: int
    subtotal: float


class CartOut(BaseModel):
    items: list[CartItemOut]
    total: float


class CheckoutResponse(BaseModel):
    order_id: int
    total: float


def _get_cart_rows(session: Session, user_id: int) -> list[tuple[CartItem, Listing]]:
    stmt = (
        select(CartItem, Listing)
        .join(Listing, Listing.id == CartItem.listing_id)
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.id)
    )
    return session.exec(stmt).all()


@router.get("", response_model=CartOut)
def get_cart(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CartOut:
    items: list[CartItemOut] = []
    for ci, listing in _get_cart_rows(session, user.id):
        items.append(
            CartItemOut(
                listing_id=listing.id,
                title=listing.title,
                price=listing.price,
                qty=ci.qty,
                subtotal=round(listing.price * ci.qty, 2),
            )
        )
    return CartOut(items=items, total=round(sum(i.subtotal for i in items), 2))


@router.post("/items", response_model=CartItemOut, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    payload: CartAddRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CartItemOut:
    listing = session.get(Listing, payload.listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.type != "buy_now":
        raise HTTPException(status_code=400, detail="Only buy-now listings can be added to the cart")
    if listing.quantity < payload.qty:
        raise HTTPException(status_code=400, detail="Not enough quantity available")

    existing = session.exec(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.listing_id == listing.id
        )
    ).first()
    if existing:
        existing.qty = min(existing.qty + payload.qty, 99)
        item = existing
        session.add(item)
    else:
        item = CartItem(user_id=user.id, listing_id=listing.id, qty=payload.qty)
        session.add(item)
    session.commit()
    session.refresh(item)

    return CartItemOut(
        listing_id=listing.id,
        title=listing.title,
        price=listing.price,
        qty=item.qty,
        subtotal=round(listing.price * item.qty, 2),
    )


@router.patch("/items/{listing_id}", response_model=CartItemOut)
def update_cart_item(
    listing_id: int,
    payload: CartUpdateRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CartItemOut:
    item = session.exec(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.listing_id == listing_id
        )
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not in cart")
    listing = session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.quantity < payload.qty:
        raise HTTPException(status_code=400, detail="Not enough quantity available")

    item.qty = payload.qty
    session.add(item)
    session.commit()
    session.refresh(item)

    return CartItemOut(
        listing_id=listing.id,
        title=listing.title,
        price=listing.price,
        qty=item.qty,
        subtotal=round(listing.price * item.qty, 2),
    )


@router.delete("/items/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cart_item(
    listing_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> None:
    item = session.exec(
        select(CartItem).where(
            CartItem.user_id == user.id, CartItem.listing_id == listing_id
        )
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not in cart")
    session.delete(item)
    session.commit()


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> CheckoutResponse:
    rows = _get_cart_rows(session, user.id)
    if not rows:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Group items by seller -> one Order per seller.
    by_seller: dict[int, list[tuple[CartItem, Listing]]] = {}
    for ci, listing in rows:
        by_seller.setdefault(listing.seller_id, []).append((ci, listing))

    order_ids: list[int] = []
    total_all = 0.0
    for seller_id, seller_items in by_seller.items():
        total = round(sum(li.price * ci.qty for ci, li in seller_items), 2)
        order = Order(buyer_id=user.id, seller_id=seller_id, total=total)
        session.add(order)
        session.flush()  # assign order.id
        for ci, li in seller_items:
            session.add(
                OrderItem(
                    order_id=order.id,
                    listing_id=li.id,
                    title=li.title,
                    price=li.price,
                    qty=ci.qty,
                )
            )
            # Decrement stock.
            li.quantity -= ci.qty
            session.add(li)
            # Remove cart row.
            session.delete(ci)
        order_ids.append(order.id)
        total_all += total

    session.commit()
    return CheckoutResponse(order_id=order_ids[0], total=round(total_all, 2))
