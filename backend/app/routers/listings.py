"""Listings: CRUD with seller ownership checks, filters, and buy-now purchases.

Schemas live here (not in schemas.py) per the delegation contract.
"""
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status as http_status
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, select

from ..db import get_session
from ..models import Listing, ListingType, Order, OrderItem, OrderStatus, Show, User
from ..security import get_current_user, require_seller

router = APIRouter(prefix="/listings", tags=["listings"])

CATEGORIES = [
    "Trading Cards",
    "Sneakers",
    "Collectibles",
    "Comics",
    "Electronics",
    "Fashion",
    "Toys",
    "Other",
]


def _normalize_images(v):
    """Accept a list of URLs or a comma-separated string; store comma-joined."""
    if isinstance(v, (list, tuple)):
        return ",".join(str(x).strip() for x in v if str(x).strip())
    return v


class ListingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    images: str | list[str] | None = None
    price: float | None = Field(default=None, ge=0)
    start_price: float | None = Field(default=None, ge=0)
    increment: float | None = Field(default=None, gt=0)
    category: str
    condition: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    type: Literal["auction", "buy_now"] = "buy_now"
    show_id: int | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        return v

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, v: str) -> str:
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(CATEGORIES)}")
        return v

    @field_validator("images", mode="before")
    @classmethod
    def images_to_csv(cls, v):
        return _normalize_images(v)


class ListingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    images: str | list[str] | None = None
    price: float | None = Field(default=None, ge=0)
    start_price: float | None = Field(default=None, ge=0)
    increment: float | None = Field(default=None, gt=0)
    category: str | None = None
    condition: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    type: Literal["auction", "buy_now"] | None = None
    show_id: int | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        return v

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(CATEGORIES)}")
        return v

    @field_validator("images", mode="before")
    @classmethod
    def images_to_csv(cls, v):
        return _normalize_images(v)


class BuyRequest(BaseModel):
    quantity: int = Field(default=1, ge=1)


class BuyResponse(BaseModel):
    order_id: int
    status: OrderStatus
    total: float


def _get_listing_or_404(listing_id: int, session: Session) -> Listing:
    listing = session.get(Listing, listing_id)
    if listing is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing


def _get_owned_listing(listing_id: int, user: User, session: Session) -> Listing:
    listing = _get_listing_or_404(listing_id, session)
    if listing.seller_id != user.id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not your listing")
    return listing


def _validate_show(show_id: int, seller_id: int, session: Session) -> None:
    """A listing can only reference a show that exists and belongs to the seller."""
    show = session.get(Show, show_id)
    if show is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Show not found")
    if show.seller_id != seller_id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Show belongs to another seller",
        )


@router.get("", response_model=list[Listing])
def list_listings(
    category: str | None = None,
    seller_id: int | None = None,
    type: Literal["auction", "buy_now"] | None = None,
    show_id: int | None = None,
    session: Session = Depends(get_session),
) -> list[Listing]:
    stmt = select(Listing)
    if category:
        stmt = stmt.where(Listing.category == category)
    if seller_id is not None:
        stmt = stmt.where(Listing.seller_id == seller_id)
    if type is not None:
        stmt = stmt.where(Listing.type == ListingType(type))
    if show_id is not None:
        stmt = stmt.where(Listing.show_id == show_id)
    stmt = stmt.order_by(Listing.created_at.desc())
    return session.exec(stmt).all()


@router.get("/{listing_id}", response_model=Listing)
def get_listing(listing_id: int, session: Session = Depends(get_session)) -> Listing:
    return _get_listing_or_404(listing_id, session)


@router.post("", response_model=Listing, status_code=http_status.HTTP_201_CREATED)
def create_listing(
    payload: ListingCreate,
    user: User = Depends(require_seller),
    session: Session = Depends(get_session),
) -> Listing:
    if payload.show_id is not None:
        _validate_show(payload.show_id, user.id, session)
    listing = Listing(
        seller_id=user.id,
        show_id=payload.show_id,
        type=ListingType(payload.type),
        title=payload.title,
        description=payload.description or "",
        images=payload.images or "",
        price=payload.price or 0.0,
        start_price=payload.start_price or 0.0,
        increment=payload.increment or 1.0,
        category=payload.category,
        condition=payload.condition or "",
        quantity=payload.quantity or 1,
    )
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return listing


@router.patch("/{listing_id}", response_model=Listing)
def update_listing(
    listing_id: int,
    payload: ListingUpdate,
    user: User = Depends(require_seller),
    session: Session = Depends(get_session),
) -> Listing:
    listing = _get_owned_listing(listing_id, user, session)
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    if "show_id" in data and data["show_id"] is not None:
        _validate_show(data["show_id"], user.id, session)
    for field, value in data.items():
        if field == "type" and value is not None:
            value = ListingType(value)
        setattr(listing, field, value)
    session.add(listing)
    session.commit()
    session.refresh(listing)
    return listing


@router.delete("/{listing_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing_id: int,
    user: User = Depends(require_seller),
    session: Session = Depends(get_session),
) -> Response:
    listing = _get_owned_listing(listing_id, user, session)
    session.delete(listing)
    session.commit()
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post("/{listing_id}/buy", response_model=BuyResponse, status_code=http_status.HTTP_201_CREATED)
def buy_listing(
    listing_id: int,
    payload: BuyRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> BuyResponse:
    """Buy-now purchase: validates type/stock, decrements quantity, creates Order + OrderItem."""
    listing = _get_listing_or_404(listing_id, session)
    if listing.type != ListingType.buy_now:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Only buy-now listings can be purchased",
        )
    if payload.quantity > listing.quantity:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Not enough stock",
        )

    listing.quantity -= payload.quantity
    order = Order(
        buyer_id=user.id,
        seller_id=listing.seller_id,
        status=OrderStatus.pending,
        total=round(listing.price * payload.quantity, 2),
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    session.add(
        OrderItem(
            order_id=order.id,
            listing_id=listing.id,
            title=listing.title,
            price=listing.price,
            qty=payload.quantity,
        )
    )
    session.commit()
    return BuyResponse(order_id=order.id, status=order.status, total=order.total)
