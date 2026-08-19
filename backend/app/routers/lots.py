"""Lots: attach auction listings to a show as ordered lots.

The realtime auction engine (realtime/auction.py) walks a show's lots in
``order_index`` order and opens them one at a time, so lot creation is a
simple, ownership-checked append here. Schemas live in this file per the
delegation contract.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from pydantic import BaseModel
from sqlmodel import Session, func, select

from ..db import get_session
from ..models import Listing, ListingType, Lot, LotStatus, Show, User
from ..security import require_seller

router = APIRouter(prefix="/shows", tags=["lots"])


class LotCreate(BaseModel):
    listing_id: int


class LotPublic(BaseModel):
    id: int
    show_id: int
    listing_id: int
    order_index: int
    status: LotStatus
    current_bid: float
    current_bidder_id: int | None = None
    ends_at: datetime | None = None


def _get_show_or_404(show_id: int, session: Session) -> Show:
    show = session.get(Show, show_id)
    if show is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Show not found")
    return show


def _to_public(lot: Lot) -> LotPublic:
    return LotPublic(
        id=lot.id,
        show_id=lot.show_id,
        listing_id=lot.listing_id,
        order_index=lot.order_index,
        status=lot.status,
        current_bid=lot.current_bid,
        current_bidder_id=lot.current_bidder_id,
        ends_at=lot.ends_at,
    )


@router.get("/{show_id}/lots", response_model=list[LotPublic])
def list_lots(
    show_id: int,
    session: Session = Depends(get_session),
) -> list[LotPublic]:
    """List a show's lots, ordered by order_index."""
    _get_show_or_404(show_id, session)
    lots = session.exec(
        select(Lot)
        .where(Lot.show_id == show_id)
        .order_by(Lot.order_index)
    ).all()
    return [_to_public(l) for l in lots]


@router.post("/{show_id}/lots", response_model=LotPublic, status_code=http_status.HTTP_201_CREATED)
def create_lot(
    show_id: int,
    payload: LotCreate,
    seller: User = Depends(require_seller),
    session: Session = Depends(get_session),
) -> LotPublic:
    """Add an auction listing owned by the show's seller as the next lot."""
    show = _get_show_or_404(show_id, session)
    if show.seller_id != seller.id:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Not your show")

    listing = session.get(Listing, payload.listing_id)
    if listing is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Listing not found")
    if listing.type != ListingType.auction:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Only auction listings can be added as lots",
        )
    if listing.seller_id != seller.id:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Listing belongs to another seller",
        )

    # order_index = current lot count for this show (append at the end).
    count = session.exec(
        select(func.count(Lot.id)).where(Lot.show_id == show_id)
    ).one()
    lot = Lot(
        show_id=show_id,
        listing_id=listing.id,
        order_index=int(count),
        status=LotStatus.pending,
    )
    session.add(lot)
    session.commit()
    session.refresh(lot)
    return _to_public(lot)
