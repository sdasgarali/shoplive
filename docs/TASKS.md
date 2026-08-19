# ShopLive — Task Board (super-boss → Hermes → OpenClaw)

Ownership legend: **[SB]** super-boss (Claude, hard core) · **[H]** Hermes (boss, integrates) · **[OC]** OpenClaw (worker, builds slices).
Partition rule: no two agents edit the same file in the same slice. Backend = `backend/`, Frontend = `frontend/`. Always `git pull --rebase` before push.

## Phase 0 — Foundation  ✅ (SB)
- [x] Repo `sdasgarali/shoplive` + Hermes/OpenClaw push access (deploy keys)
- [x] Monorepo scaffold + docs (SPEC, ARCHITECTURE, TASKS)
- [x] Backend skeleton (FastAPI app boots, `/health`) + frontend skeleton
- [x] [SB] Data model + DB + auth (JWT)

## Phase 1 — Core backend  ✅
- [x] [SB] `models.py` + `db.py` + `security.py` (JWT, hashing, current-user dep)
- [x] [SB] `routers/auth.py` (register/login/me) + tests
- [x] [SB] Realtime engine: `realtime/rooms.py`, `chat.py`, `auction.py` (bid validation, anti-snipe timer, winner→order) + tests, WS verified live
- [x] [OC] `routers/shows.py` — discovery feed, category filter, show CRUD (ownership-checked) + tests
- [x] [OC] `routers/listings.py` — listing CRUD, buy-now + tests
- [x] [OC] `routers/sellers.py` — storefront + follow/unfollow + tests
- [x] [H] `routers/cart.py` + `routers/orders.py` — cart→checkout→orders + tests
- [x] [SB] `seed.py` — demo sellers/shows/lots (1 live show w/ 3 auction lots)

## Phase 2 — Frontend  ✅ (built by SB)
- [x] [SB] `lib/api.ts`, `lib/ws.ts`, `lib/auth.tsx` (auth context, token storage)
- [x] Components: `NavBar`, `ShowCard`, `ChatPanel`, `AuctionPanel`, `BuyNowRail`
- [x] `app/page.tsx` discovery feed (live/upcoming, category + search)
- [x] `app/login` + `app/signup` (calls auth API, stores token)
- [x] `app/seller/[id]` storefront + follow button
- [x] `app/show/[id]` — player + ChatPanel + AuctionPanel + BuyNowRail (live WS)
- [x] `app/cart` + `app/orders`
- [ ] [OC] `app/seller/hub` — create show, add lots, run-auction controls
- [x] [H] `routers/lots.py` — add auction listings to shows as ordered lots, ownership-checked + tests
- [x] [OC] `app/seller/hub/page.tsx` — create show, manage status, add listings + lots, lots panel

## Phase 3 — Polish & integration
- [x] [SB] End-to-end run verified — REST + live auction WS bid PASS, `next build` clean, 32 backend tests green
- [x] [SB] Dockerfile(s) + `docker-compose.yml` (api + web + postgres + redis), Postgres switch
- [x] [SB] `.env.example` (all service keys incl. later Stripe/Mux/S3)
- [ ] README run docs / demo walkthrough  (partly done)
- [ ] [SB] CI (GitHub Actions: backend pytest + frontend build/lint)  (next)

**MVP status: shippable.** Buyer flow works end-to-end (browse → live show → chat → bid → win/buy → cart → checkout → orders). Remaining: seller hub UI, CI, and the "later services" (real video, payments).

## Delegation protocol for this project
1. **SB** posts a task package to the Workplace group tagging **@HermanoforzBot** (goal, which files, acceptance, "assign OpenClaw the [OC] items").
2. **Hermes** breaks it down, does [H] items, and delegates [OC] items to **@Newra_openclaw_bot**.
3. **OpenClaw** builds its slice in its folder, pushes to `main`, tags Hermes back.
4. **Hermes** integrates, verifies, reports up to SB.
Repo push (bots): `git clone git@github-shoplive:sdasgarali/shoplive.git` (deploy key preconfigured).
