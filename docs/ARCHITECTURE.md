# ShopLive — Architecture

## Stack
- **Frontend:** Next.js (App Router) + TypeScript + Tailwind CSS. Mobile-first. Data via `fetch` to the backend; live features via native WebSocket.
- **Backend:** FastAPI (Python 3.11+). REST for CRUD; WebSocket endpoints for chat + auctions. SQLModel/SQLAlchemy ORM.
- **DB:** SQLite for local dev (`shoplive.db`), Postgres-ready via `DATABASE_URL`.
- **Auth:** JWT (access token) via `python-jose`, passwords hashed with `passlib[bcrypt]`.
- **Realtime:** in-process room registry + `asyncio` broadcast. A single auction "engine" task per live show advances lots on a timer. (Redis pub/sub is a later upgrade for multi-process.)

## Backend layout
```
backend/
├── app/
│   ├── main.py            # FastAPI app, router includes, CORS, WS mounts
│   ├── config.py          # settings from env (DATABASE_URL, JWT_SECRET, ...)
│   ├── db.py              # engine, session, init
│   ├── models.py          # User, Seller, Show, Listing, Lot, Bid, Order, Follow, ChatMessage
│   ├── schemas.py         # Pydantic request/response models
│   ├── security.py        # hashing, JWT, current-user dependency
│   ├── routers/
│   │   ├── auth.py        # /auth/register, /auth/login, /auth/me
│   │   ├── shows.py       # /shows CRUD, /shows/{id}, discovery feed, categories
│   │   ├── listings.py    # /listings CRUD, buy-now
│   │   ├── sellers.py     # /sellers/{id} storefront, follow
│   │   ├── cart.py        # cart + checkout -> orders
│   │   └── orders.py      # buyer/seller orders
│   ├── realtime/
│   │   ├── rooms.py       # room/connection manager, broadcast
│   │   ├── chat.py        # WS /ws/shows/{id}/chat
│   │   └── auction.py     # WS /ws/shows/{id}/auction + engine (bid validation, timer, winner)
│   └── seed.py            # demo sellers/shows/listings for local dev
├── tests/                 # pytest (auth, listings, auction engine, checkout)
└── requirements.txt
```

## Frontend layout
```
frontend/
├── app/
│   ├── layout.tsx, globals.css
│   ├── page.tsx                 # discovery feed (live + upcoming)
│   ├── category/[slug]/page.tsx
│   ├── show/[id]/page.tsx       # live show: player + chat + auction + buy-now
│   ├── seller/[id]/page.tsx     # storefront
│   ├── cart/page.tsx, orders/page.tsx
│   ├── login/page.tsx, signup/page.tsx
│   └── seller/hub/page.tsx      # create show, add lots, run auction
├── components/                  # ShowCard, LiveBadge, ChatPanel, AuctionPanel, BuyNowRail, NavBar, ...
├── lib/
│   ├── api.ts                   # REST client (reads NEXT_PUBLIC_API_URL)
│   ├── ws.ts                    # WebSocket helpers (chat, auction)
│   └── auth.ts                  # token storage, auth context
└── package.json
```

## Data model (core entities)
- **User**(id, email, password_hash, username, is_seller, created_at)
- **Seller**(user_id, bio, rating, follower_count)
- **Show**(id, seller_id, title, category, status[scheduled|live|ended], scheduled_at, viewer_count, thumbnail_url)
- **Listing**(id, seller_id, show_id?, type[auction|buy_now], title, description, images, price, start_price, increment, category, condition, quantity)
- **Lot**(id, show_id, listing_id, order_index, status[pending|open|sold|unsold], current_bid, current_bidder_id, ends_at)
- **Bid**(id, lot_id, user_id, amount, created_at)
- **Order**(id, buyer_id, seller_id, status, total, created_at) + **OrderItem**(order_id, listing_id, title, price, qty)
- **Follow**(user_id, seller_id)
- **ChatMessage**(id, show_id, user_id, username, text, created_at)

## Conventions
Enterprise-grade: input validation, error handling, JWT-guarded mutations, ownership checks (a seller only edits their own shows/listings), tests per router + the auction engine. Config via env; secrets never committed. Small PRs per slice.
