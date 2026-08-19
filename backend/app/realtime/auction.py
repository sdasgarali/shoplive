"""Live auction engine + WebSocket endpoint.

Per live show, an in-memory engine walks the show's lots in order: it opens a
lot, accepts bids over WebSocket, runs a countdown (with anti-snipe extension),
then settles the lot — creating an Order for the winner — and advances. All
state changes are broadcast to the show's ``auction:<id>`` room.

The pure helpers (:func:`min_next_bid`, :func:`validate_bid`, :func:`settle_lot`)
carry the business rules and are unit-tested without any WebSocket plumbing.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlmodel import Session, select

from ..config import settings
from ..db import engine as db_engine
from ..models import (
    Bid, Listing, ListingType, Lot, LotStatus, Order, OrderItem, OrderStatus, Show, User,
)
from .rooms import rooms

router = APIRouter(tags=["realtime"])

LOT_DURATION_SECONDS = 30      # countdown per lot
ANTISNIPE_SECONDS = 5          # a bid within this window extends the timer...
ANTISNIPE_EXTEND_TO = 8        # ...to this many seconds remaining


# ── pure business rules (unit-tested) ────────────────────────────────────────
def min_next_bid(lot: Lot, listing: Listing) -> float:
    """Smallest acceptable bid for a lot right now."""
    if lot.current_bidder_id is None:
        return round(listing.start_price, 2)
    return round(lot.current_bid + listing.increment, 2)


def validate_bid(amount: float, lot: Lot, listing: Listing) -> tuple[bool, str]:
    if lot.status != LotStatus.open:
        return False, "Lot is not open for bidding"
    floor = min_next_bid(lot, listing)
    if amount < floor:
        return False, f"Bid must be at least {floor:.2f}"
    return True, ""


def settle_lot(session: Session, lot: Lot) -> Order | None:
    """Close a lot: sold (create Order+OrderItem for the winner) or unsold."""
    listing = session.get(Listing, lot.listing_id)
    if lot.current_bidder_id is not None and listing is not None:
        lot.status = LotStatus.sold
        order = Order(
            buyer_id=lot.current_bidder_id,
            seller_id=listing.seller_id,
            status=OrderStatus.pending,
            total=round(lot.current_bid, 2),
        )
        session.add(order)
        session.flush()
        session.add(OrderItem(
            order_id=order.id, listing_id=listing.id,
            title=listing.title, price=round(lot.current_bid, 2), qty=1,
        ))
        session.add(lot)
        session.commit()
        session.refresh(order)
        return order
    lot.status = LotStatus.unsold
    session.add(lot)
    session.commit()
    return None


# ── auth over websocket (token in query string) ──────────────────────────────
def _user_from_token(token: str | None, session: Session) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return session.get(User, int(payload.get("sub")))
    except (JWTError, TypeError, ValueError):
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── per-show engine ───────────────────────────────────────────────────────────
class ShowAuction:
    def __init__(self, show_id: int) -> None:
        self.show_id = show_id
        self.room = f"auction:{show_id}"
        self.lock = asyncio.Lock()
        self.task: asyncio.Task | None = None
        self.current: Lot | None = None
        self.listing: Listing | None = None
        self.ends_at: datetime | None = None

    def snapshot(self) -> dict:
        lot, listing = self.current, self.listing
        if lot is None or listing is None:
            return {"type": "auction_idle", "show_id": self.show_id}
        secs = 0
        if self.ends_at:
            secs = max(0, int((self.ends_at - _now()).total_seconds()))
        return {
            "type": "lot_state",
            "show_id": self.show_id,
            "lot_id": lot.id,
            "title": listing.title,
            "images": listing.images,
            "current_bid": round(lot.current_bid, 2),
            "current_bidder_id": lot.current_bidder_id,
            "min_next_bid": min_next_bid(lot, listing),
            "seconds_left": secs,
            "status": lot.status.value,
        }

    async def place_bid(self, user: User, amount: float) -> tuple[bool, str]:
        async with self.lock:
            if self.current is None or self.listing is None:
                return False, "No lot is currently open"
            ok, err = validate_bid(amount, self.current, self.listing)
            if not ok:
                return False, err
            with Session(db_engine) as s:
                lot = s.get(Lot, self.current.id)
                lot.current_bid = round(amount, 2)
                lot.current_bidder_id = user.id
                s.add(lot)
                s.add(Bid(lot_id=lot.id, user_id=user.id, amount=round(amount, 2)))
                s.commit()
                s.refresh(lot)
                self.current = lot
            # anti-snipe: extend the clock if the bid landed in the final seconds
            if self.ends_at and (self.ends_at - _now()).total_seconds() < ANTISNIPE_SECONDS:
                from datetime import timedelta
                self.ends_at = _now() + timedelta(seconds=ANTISNIPE_EXTEND_TO)
            return True, ""

    async def run(self) -> None:
        """Walk the show's pending lots, one at a time, to completion."""
        from datetime import timedelta
        try:
            while True:
                with Session(db_engine) as s:
                    lot = s.exec(
                        select(Lot)
                        .where(Lot.show_id == self.show_id, Lot.status == LotStatus.pending)
                        .order_by(Lot.order_index)
                    ).first()
                    if lot is None:
                        break
                    lot.status = LotStatus.open
                    s.add(lot)
                    s.commit()
                    s.refresh(lot)
                    listing = s.get(Listing, lot.listing_id)
                async with self.lock:
                    self.current, self.listing = lot, listing
                    self.ends_at = _now() + timedelta(seconds=LOT_DURATION_SECONDS)
                await rooms.broadcast(self.room, {**self.snapshot(), "type": "lot_open"})

                while self.ends_at and _now() < self.ends_at:
                    await asyncio.sleep(1)
                    await rooms.broadcast(self.room, self.snapshot())

                with Session(db_engine) as s:
                    lot = s.get(Lot, self.current.id)
                    order = settle_lot(s, lot)
                    result = {
                        "type": "lot_closed",
                        "lot_id": lot.id,
                        "status": lot.status.value,
                        "winner_id": lot.current_bidder_id,
                        "final_bid": round(lot.current_bid, 2),
                        "order_id": order.id if order else None,
                    }
                async with self.lock:
                    self.current = self.listing = self.ends_at = None
                await rooms.broadcast(self.room, result)

            await rooms.broadcast(self.room, {"type": "auction_ended", "show_id": self.show_id})
        finally:
            _engines.pop(self.show_id, None)


_engines: dict[int, ShowAuction] = {}


def ensure_engine(show_id: int) -> ShowAuction:
    eng = _engines.get(show_id)
    if eng is None:
        eng = ShowAuction(show_id)
        _engines[show_id] = eng
    if eng.task is None or eng.task.done():
        with Session(db_engine) as s:
            pending = s.exec(
                select(Lot).where(Lot.show_id == show_id, Lot.status == LotStatus.pending)
            ).first()
        if pending is not None:
            eng.task = asyncio.create_task(eng.run())
    return eng


@router.websocket("/ws/shows/{show_id}/auction")
async def auction_ws(ws: WebSocket, show_id: int, token: str | None = None):
    await ws.accept()
    with Session(db_engine) as s:
        if s.get(Show, show_id) is None:
            await ws.close(code=4404)
            return
        user = _user_from_token(token, s)

    eng = ensure_engine(show_id)
    await rooms.join(eng.room, ws)
    await ws.send_json(eng.snapshot())
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "bid":
                if user is None:
                    await ws.send_json({"type": "error", "error": "Log in to bid"})
                    continue
                try:
                    amount = float(data.get("amount"))
                except (TypeError, ValueError):
                    await ws.send_json({"type": "error", "error": "Invalid amount"})
                    continue
                ok, err = await eng.place_bid(user, amount)
                if not ok:
                    await ws.send_json({"type": "error", "error": err})
                else:
                    await rooms.broadcast(eng.room, {**eng.snapshot(), "type": "new_bid"})
    except WebSocketDisconnect:
        await rooms.leave(eng.room, ws)
    except Exception:
        await rooms.leave(eng.room, ws)
