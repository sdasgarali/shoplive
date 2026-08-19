# ShopLive — Product Spec (MVP)

An original live-shopping marketplace. Feature set below is derived from the live-commerce category in general; all copy, branding, and assets are our own.

## Personas
- **Buyer** — discovers shows, watches live, bids/buys, chats, follows sellers, manages cart & orders.
- **Seller** — creates & runs live shows, lists items (auction / buy-now), manages orders & earnings.
- **Guest** — can browse and watch; must sign up to bid, buy, chat, or follow.

## Core features (MVP)
1. **Auth** — email/password sign up + login (JWT). Roles: buyer, seller (a user can be both).
2. **Discovery feed** — home grid of **Live now** + **Upcoming** shows, with category filter and search. Each card: thumbnail, title, seller, viewer count, category, live/scheduled badge.
3. **Categories** — browse by category (Trading Cards, Sneakers, Collectibles, Comics, Electronics, Fashion, Toys, Other). Category page lists shows + featured listings.
4. **Live show page** — the heart of the app:
   - Video area (MVP: a placeholder/looping player or HLS test stream; real ingest is out of MVP scope).
   - **Live chat** (WebSocket) — messages with username, timestamp; system messages for sold items.
   - **Auction panel** (WebSocket) — current lot, current highest bid + bidder, bid increment, countdown timer, **Place Bid** button; auto-advances to next lot; announces winner.
   - **Buy Now rail** — fixed-price items in the show; add to cart / buy instantly.
   - Viewer count, follow-seller button.
5. **Listings** — an item belongs to a seller and optionally a show. Type = `auction` or `buy_now`. Fields: title, description, images, price/start price, increment, category, condition, quantity.
6. **Seller storefront** — public profile: bio, rating, follower count, current/upcoming shows, buy-now listings, follow button.
7. **Cart & checkout** — cart of buy-now items + won auctions; mock checkout (no real payment in MVP) → creates an Order.
8. **Orders** — buyer order history + status (pending, paid, shipped); seller order queue.
9. **Follow & notifications** — follow sellers; "live soon" notification list (in-app).
10. **Seller hub** — create show (schedule/go live), add listings to a show, run the auction (advance lots), basic earnings summary.

## Real-time behaviors
- **Chat:** clients join a show room over WS; broadcast messages to the room.
- **Auction:** server holds authoritative lot state; bids validated (>= current + increment, auction open); on timer expiry, lot closes, winner recorded, order line created, next lot opens. All state changes broadcast to the room.

## Out of scope (MVP)
Real video ingest/streaming (WebRTC/RTMP), real payments/payouts, shipping labels, mobile native apps, moderation/anti-fraud, recommendations. Design so these can be added later.

## Acceptance (MVP "done")
A buyer can: sign up → open a live show → send chat → place a winning bid on a lot → see it in cart → checkout → see the order. A seller can: create a show → add lots → go live → run the auction → see the resulting order. Frontend talks to backend over REST + WS; everything runs locally with `uvicorn` + `next dev`.
