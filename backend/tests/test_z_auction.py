"""Auction engine business-rule tests (no WebSocket plumbing)."""
import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from sqlmodel import Session  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.models import (  # noqa: E402
    Listing, ListingType, Lot, LotStatus, Order, Seller, User,
)
from app.realtime.auction import min_next_bid, validate_bid, settle_lot  # noqa: E402

init_db()


_seq = 0


def _fixtures(session: Session):
    global _seq
    _seq += 1
    seller = User(email=f"s{_seq}@x.com", username=f"s{_seq}", password_hash="x", is_seller=True)
    buyer = User(email=f"b{_seq}@x.com", username=f"b{_seq}", password_hash="x")
    session.add(seller); session.add(buyer); session.commit()
    session.refresh(seller); session.refresh(buyer)
    session.add(Seller(user_id=seller.id, display_name="S")); session.commit()
    listing = Listing(seller_id=seller.id, type=ListingType.auction, title="Card",
                      category="Trading Cards", start_price=50.0, increment=5.0)
    session.add(listing); session.commit(); session.refresh(listing)
    lot = Lot(show_id=1, listing_id=listing.id, status=LotStatus.open)
    session.add(lot); session.commit(); session.refresh(lot)
    return seller, buyer, listing, lot


def test_min_next_bid_first_and_subsequent():
    with Session(engine) as s:
        _, buyer, listing, lot = _fixtures(s)
        # No bids yet -> must meet start_price.
        assert min_next_bid(lot, listing) == 50.0
        # After a bid -> current + increment.
        lot.current_bid = 50.0
        lot.current_bidder_id = buyer.id
        assert min_next_bid(lot, listing) == 55.0


def test_validate_bid_rules():
    with Session(engine) as s:
        _, buyer, listing, lot = _fixtures(s)
        ok, err = validate_bid(49.0, lot, listing)
        assert not ok and "at least" in err
        ok, _ = validate_bid(50.0, lot, listing)
        assert ok
        # A closed lot rejects all bids.
        lot.status = LotStatus.unsold
        ok, err = validate_bid(999.0, lot, listing)
        assert not ok


def test_settle_lot_creates_order_for_winner():
    with Session(engine) as s:
        seller, buyer, listing, lot = _fixtures(s)
        lot.current_bid = 65.0
        lot.current_bidder_id = buyer.id
        s.add(lot); s.commit()
        order = settle_lot(s, lot)
        assert order is not None
        assert order.buyer_id == buyer.id
        assert order.seller_id == seller.id
        assert order.total == 65.0
        assert lot.status == LotStatus.sold


def test_settle_lot_unsold_when_no_bidder():
    with Session(engine) as s:
        _, _, _, lot = _fixtures(s)
        order = settle_lot(s, lot)
        assert order is None
        assert lot.status == LotStatus.unsold
