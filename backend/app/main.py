"""ShopLive API — FastAPI application entrypoint.

Boots the DB, mounts CORS, and includes routers. Additional routers
(shows, listings, sellers, cart, orders) and the realtime WS endpoints are
added by the team as those slices land — see docs/TASKS.md.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .realtime import auction, chat
from .routers import auth, cart, listings, orders, sellers, shows


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="ShopLive API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(shows.router)
app.include_router(listings.router)
app.include_router(sellers.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(chat.router)
app.include_router(auction.router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": "shoplive-api", "version": app.version}
