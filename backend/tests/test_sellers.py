"""Sellers router tests: storefront, follow/unfollow, auth + edge cases."""
import os
import tempfile

# Throwaway SQLite per test session — set BEFORE importing app (same pattern as test_auth.py).
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routers.sellers import router as sellers_router  # noqa: E402

# main.py is wired by Hermes; include the router here so this slice is testable now.
if not any(getattr(r, "path", None) == "/sellers" for r in app.routes):
    app.include_router(sellers_router)

init_db()
client = TestClient(app)


def _auth(email: str, username: str, *, is_seller: bool = False, display_name: str | None = None) -> dict:
    body = {"email": email, "username": username, "password": "supersecret", "is_seller": is_seller}
    if display_name:
        body["display_name"] = display_name
    r = client.post("/auth/register", json=body)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _seller_id(headers: dict) -> int:
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    return r.json()["id"]


def test_storefront():
    seller_headers = _auth("sell_seller1@test.dev", "sellseller1", is_seller=True, display_name="Sneaker Sam")
    seller_id = _seller_id(seller_headers)

    # A show + a buy-now listing + an auction listing
    r = client.post("/shows", json={"title": "Sam's Drop", "category": "Sneakers"}, headers=seller_headers)
    assert r.status_code == 201, r.text
    r = client.post("/listings", json={"title": "Yeezy 350", "category": "Sneakers", "type": "buy_now", "price": 300.0}, headers=seller_headers)
    assert r.status_code == 201, r.text
    client.post("/listings", json={"title": "Auction Pair", "category": "Sneakers", "type": "auction", "start_price": 100.0}, headers=seller_headers)

    r = client.get(f"/sellers/{seller_id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["display_name"] == "Sneaker Sam"
    assert body["bio"] == ""
    assert body["rating"] == 0.0
    assert body["follower_count"] == 0
    assert any(s["title"] == "Sam's Drop" for s in body["shows"])
    assert any(l["title"] == "Yeezy 350" for l in body["listings"])
    # Buy-now listings only — the auction listing must not appear
    assert all(l["type"] == "buy_now" for l in body["listings"])
    assert all(l["title"] != "Auction Pair" for l in body["listings"])


def test_storefront_unknown_seller():
    assert client.get("/sellers/99999").status_code == 404


def test_follow_unfollow_cycle():
    seller_headers = _auth("sell_seller2@test.dev", "sellseller2", is_seller=True, display_name="Comic Connie")
    seller_id = _seller_id(seller_headers)
    buyer = _auth("sell_buyer1@test.dev", "sellbuyer1")

    # Follow
    r = client.post(f"/sellers/{seller_id}/follow", headers=buyer)
    assert r.status_code == 201, r.text
    assert r.json()["follower_count"] == 1
    assert client.get(f"/sellers/{seller_id}").json()["follower_count"] == 1

    # Duplicate follow → 409, count unchanged
    r = client.post(f"/sellers/{seller_id}/follow", headers=buyer)
    assert r.status_code == 409
    assert client.get(f"/sellers/{seller_id}").json()["follower_count"] == 1

    # Unfollow → decrement
    r = client.delete(f"/sellers/{seller_id}/follow", headers=buyer)
    assert r.status_code == 200
    assert r.json()["follower_count"] == 0
    assert client.get(f"/sellers/{seller_id}").json()["follower_count"] == 0

    # Unfollow again → 404
    assert client.delete(f"/sellers/{seller_id}/follow", headers=buyer).status_code == 404


def test_follow_edge_cases():
    seller_headers = _auth("sell_seller3@test.dev", "sellseller3", is_seller=True)
    seller_id = _seller_id(seller_headers)
    buyer = _auth("sell_buyer2@test.dev", "sellbuyer2")

    # Unauthenticated
    assert client.post(f"/sellers/{seller_id}/follow").status_code == 401
    assert client.delete(f"/sellers/{seller_id}/follow").status_code == 401

    # Unknown seller
    assert client.post("/sellers/99999/follow", headers=buyer).status_code == 404
    assert client.delete("/sellers/99999/follow", headers=buyer).status_code == 404

    # Self-follow → 400
    assert client.post(f"/sellers/{seller_id}/follow", headers=seller_headers).status_code == 400
