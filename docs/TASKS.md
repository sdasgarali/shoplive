# ShopLive — Task Board (super-boss → Hermes → OpenClaw)

Ownership legend: **[SB]** super-boss (Claude, hard core) · **[H]** Hermes (boss, integrates) · **[OC]** OpenClaw (worker, builds slices).
Partition rule: no two agents edit the same file in the same slice. Backend = `backend/`, Frontend = `frontend/`. Always `git pull --rebase` before push.

## Phase 0 — Foundation  ✅ (SB)
- [x] Repo `sdasgarali/shoplive` + Hermes/OpenClaw push access (deploy keys)
- [x] Monorepo scaffold + docs (SPEC, ARCHITECTURE, TASKS)
- [x] Backend skeleton (FastAPI app boots, `/health`) + frontend skeleton
- [ ] Data model + DB + auth (JWT)  ← SB owns (hard core)

## Phase 1 — Core backend (mostly SB, with OC slices)
- [ ] [SB] `models.py` + `db.py` + `security.py` (JWT, hashing, current-user dep)
- [ ] [SB] `routers/auth.py` (register/login/me) + tests
- [ ] [SB] Realtime engine: `realtime/rooms.py`, `chat.py`, `auction.py` (bid validation, timer, winner) + tests
- [ ] [OC] `routers/shows.py` — discovery feed, category filter, show CRUD (ownership-checked) + tests
- [ ] [OC] `routers/listings.py` — listing CRUD, buy-now + tests
- [ ] [OC] `routers/sellers.py` — storefront + follow/unfollow + tests
- [ ] [H] `routers/cart.py` + `routers/orders.py` — cart→checkout→orders (integrates auction wins) + tests
- [ ] [SB] `seed.py` — demo sellers/shows/lots so the app is explorable

## Phase 2 — Frontend (OC builds components, H wires pages, SB does realtime)
- [ ] [SB] `lib/api.ts`, `lib/ws.ts`, `lib/auth.ts` (auth context, token storage)
- [ ] [OC] Components: `NavBar`, `ShowCard`, `LiveBadge`, `CategoryChips`, `Footer`
- [ ] [OC] `app/page.tsx` discovery feed + `app/category/[slug]/page.tsx`
- [ ] [OC] `app/login` + `app/signup` (calls auth API, stores token)
- [ ] [OC] `app/seller/[id]` storefront + follow button
- [ ] [SB] `components/ChatPanel` + `components/AuctionPanel` (WebSocket, live bids/timer)
- [ ] [H] `app/show/[id]/page.tsx` — assemble player + ChatPanel + AuctionPanel + BuyNowRail
- [ ] [H] `app/cart` + `app/orders`
- [ ] [OC] `app/seller/hub` — create show, add lots, run-auction controls

## Phase 3 — Polish & integration (H + SB)
- [ ] [H] End-to-end wire-up, fix cross-cutting bugs, run both, verify acceptance flow
- [ ] [SB] Dockerfile(s) + `docker-compose.yml` (api + web + postgres), Postgres switch
- [ ] [H] README run docs, seed script, demo walkthrough
- [ ] [SB] CI (GitHub Actions: backend pytest + frontend build/lint)

## Delegation protocol for this project
1. **SB** posts a task package to the Workplace group tagging **@HermanoforzBot** (goal, which files, acceptance, "assign OpenClaw the [OC] items").
2. **Hermes** breaks it down, does [H] items, and delegates [OC] items to **@Newra_openclaw_bot**.
3. **OpenClaw** builds its slice in its folder, pushes to `main`, tags Hermes back.
4. **Hermes** integrates, verifies, reports up to SB.
Repo push (bots): `git clone git@github-shoplive:sdasgarali/shoplive.git` (deploy key preconfigured).
