"""Seed the database with demo sellers, shows, listings, and lots.

Run:  python -m app.seed        (from the backend/ directory)

Idempotent-ish: skips seeding if any users already exist. Delete shoplive.db to
reseed from scratch.
"""
from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session, select

from .db import engine, init_db
from .models import (
    Listing, ListingType, Lot, LotStatus, Seller, Show, ShowStatus, User,
)
from .security import hash_password
from .realtime.auction import _now

DEMO_PASSWORD = "password123"


def seed() -> None:
    init_db()
    with Session(engine) as s:
        if s.exec(select(User)).first():
            print("Database already has users — skipping seed. (Delete shoplive.db to reseed.)")
            return

        # A buyer and two sellers.
        buyer = User(email="buyer@shoplive.dev", username="buyer",
                     password_hash=hash_password(DEMO_PASSWORD))
        s.add(buyer)

        sellers_spec = [
            ("cardvault@shoplive.dev", "cardvault", "CardVault", "Graded cards & sealed wax.", "Trading Cards"),
            ("kickspot@shoplive.dev", "kickspot", "KickSpot", "Deadstock sneakers, daily drops.", "Sneakers"),
        ]
        sellers: list[User] = []
        for email, uname, display, bio, _cat in sellers_spec:
            u = User(email=email, username=uname, password_hash=hash_password(DEMO_PASSWORD), is_seller=True)
            s.add(u)
            s.flush()
            s.add(Seller(user_id=u.id, display_name=display, bio=bio, rating=4.8, follower_count=120))
            sellers.append(u)
        s.commit()
        for u in sellers:
            s.refresh(u)

        cardvault, kickspot = sellers

        # A LIVE show for CardVault, with auction lots + a buy-now item.
        live = Show(seller_id=cardvault.id, title="🔥 Live Card Break — Prizm Hobby Box",
                    category="Trading Cards", status=ShowStatus.live, viewer_count=342,
                    thumbnail_url="https://picsum.photos/seed/cards/640/360")
        s.add(live)
        s.flush()

        auction_specs = [
            ("2019 Prizm Zion RC PSA 10", 50.0, 5.0, "Collectibles"),
            ("Charizard Base Set (near mint)", 80.0, 5.0, "Trading Cards"),
            ("Sealed Prizm Hobby Box", 120.0, 10.0, "Trading Cards"),
        ]
        for i, (title, start, inc, cat) in enumerate(auction_specs):
            listing = Listing(seller_id=cardvault.id, show_id=live.id, type=ListingType.auction,
                              title=title, category=cat, start_price=start, increment=inc,
                              images=f"https://picsum.photos/seed/lot{i}/400/400")
            s.add(listing)
            s.flush()
            s.add(Lot(show_id=live.id, listing_id=listing.id, order_index=i, status=LotStatus.pending))

        s.add(Listing(seller_id=cardvault.id, show_id=live.id, type=ListingType.buy_now,
                      title="Card Sleeves (100ct)", category="Trading Cards", price=9.99, quantity=50,
                      images="https://picsum.photos/seed/sleeves/400/400"))

        # An UPCOMING show for KickSpot + some buy-now sneakers.
        upcoming = Show(seller_id=kickspot.id, title="Sneaker Sunday — Jordan Drops",
                        category="Sneakers", status=ShowStatus.scheduled,
                        scheduled_at=_now() + timedelta(hours=6),
                        thumbnail_url="https://picsum.photos/seed/kicks/640/360")
        s.add(upcoming)
        for i, (title, price) in enumerate([("Air Jordan 1 Chicago", 320.0), ("Dunk Low Panda", 140.0)]):
            s.add(Listing(seller_id=kickspot.id, type=ListingType.buy_now, title=title,
                          category="Sneakers", price=price, quantity=5,
                          images=f"https://picsum.photos/seed/shoe{i}/400/400"))

        s.commit()
        print("Seeded: 1 buyer, 2 sellers, 2 shows (1 live w/ 3 auction lots + buy-now), sneakers.")
        print(f"Demo login — buyer@shoplive.dev / {DEMO_PASSWORD}  (sellers: cardvault@, kickspot@)")


if __name__ == "__main__":
    seed()
