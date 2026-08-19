"""SQLModel ORM models — the ShopLive data model.

See docs/ARCHITECTURE.md for the entity overview. Kept in one module so all
routers (auth, shows, listings, sellers, cart, orders) share the same schema.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ShowStatus(str, Enum):
    scheduled = "scheduled"
    live = "live"
    ended = "ended"


class ListingType(str, Enum):
    auction = "auction"
    buy_now = "buy_now"


class LotStatus(str, Enum):
    pending = "pending"
    open = "open"
    sold = "sold"
    unsold = "unsold"


class OrderStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    shipped = "shipped"
    cancelled = "cancelled"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    is_seller: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_now)


class Seller(SQLModel, table=True):
    user_id: int = Field(primary_key=True, foreign_key="user.id")
    display_name: str
    bio: str = Field(default="")
    rating: float = Field(default=0.0)
    follower_count: int = Field(default=0)


class Show(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    seller_id: int = Field(foreign_key="seller.user_id", index=True)
    title: str
    category: str = Field(index=True)
    status: ShowStatus = Field(default=ShowStatus.scheduled, index=True)
    scheduled_at: Optional[datetime] = None
    viewer_count: int = Field(default=0)
    thumbnail_url: str = Field(default="")
    created_at: datetime = Field(default_factory=_now)


class Listing(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    seller_id: int = Field(foreign_key="seller.user_id", index=True)
    show_id: Optional[int] = Field(default=None, foreign_key="show.id", index=True)
    type: ListingType = Field(default=ListingType.buy_now)
    title: str
    description: str = Field(default="")
    images: str = Field(default="")  # comma-separated URLs
    price: float = Field(default=0.0)          # buy_now price
    start_price: float = Field(default=0.0)    # auction opening
    increment: float = Field(default=1.0)      # auction min raise
    category: str = Field(index=True)
    condition: str = Field(default="")
    quantity: int = Field(default=1)
    created_at: datetime = Field(default_factory=_now)


class Lot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    show_id: int = Field(foreign_key="show.id", index=True)
    listing_id: int = Field(foreign_key="listing.id")
    order_index: int = Field(default=0)
    status: LotStatus = Field(default=LotStatus.pending)
    current_bid: float = Field(default=0.0)
    current_bidder_id: Optional[int] = Field(default=None, foreign_key="user.id")
    ends_at: Optional[datetime] = None


class Bid(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    lot_id: int = Field(foreign_key="lot.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    amount: float
    created_at: datetime = Field(default_factory=_now)


class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    buyer_id: int = Field(foreign_key="user.id", index=True)
    seller_id: int = Field(foreign_key="seller.user_id", index=True)
    status: OrderStatus = Field(default=OrderStatus.pending)
    total: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=_now)


class OrderItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="order.id", index=True)
    listing_id: int = Field(foreign_key="listing.id")
    title: str
    price: float
    qty: int = Field(default=1)


class Follow(SQLModel, table=True):
    user_id: int = Field(primary_key=True, foreign_key="user.id")
    seller_id: int = Field(primary_key=True, foreign_key="seller.user_id")
    created_at: datetime = Field(default_factory=_now)


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    show_id: int = Field(foreign_key="show.id", index=True)
    user_id: int = Field(foreign_key="user.id")
    username: str
    text: str
    created_at: datetime = Field(default_factory=_now)
