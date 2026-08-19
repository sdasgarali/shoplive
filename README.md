# ShopLive

[![CI](https://github.com/sdasgarali/shoplive/actions/workflows/ci.yml/badge.svg)](https://github.com/sdasgarali/shoplive/actions/workflows/ci.yml)

An original **live-shopping marketplace** — sellers host real-time video shows, buyers bid in live auctions or buy instantly ("Buy Now"), with live chat, seller storefronts, category discovery, and a feed of live/upcoming shows.

> ShopLive is an independent project inspired by the live-commerce category. It uses its own branding, copy, and assets — it is **not** affiliated with, and does not copy the content or trademarks of, any existing platform.

## Monorepo layout
```
shopLive/
├── frontend/     Next.js (App Router) + Tailwind + TypeScript
├── backend/      FastAPI + SQLite→Postgres, REST + WebSockets
├── docs/         SPEC.md · ARCHITECTURE.md · TASKS.md
└── README.md
```

## The team (3-tier)
- **Super-boss (Claude, local):** architecture, hard core (auth, real-time auction engine, WebSockets, data model, integration), task breakdown.
- **Hermes** (`@HermanoforzBot`): boss — takes a task package, breaks it into slices, delegates to OpenClaw.
- **OpenClaw** (`@Newra_openclaw_bot`): worker — builds assigned slices.

## Quick start (local dev)
**Backend** (port 8000):
```bash
cd backend
python -m venv venv && venv/Scripts/activate   # Windows;  source venv/bin/activate on Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
**Frontend** (port 3000):
```bash
cd frontend
npm install
npm run dev
```
Frontend expects the API at `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`).

See `docs/` for the full spec, architecture, and the live task board.
