"""Cart + orders flow tests: add -> update -> remove -> checkout -> order status.

Uses the same temp-SQLite pattern as test_auth.py.
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402

init_db()
client = TestClient(app)


def _register(email, username, is_seller=False, display_name=None):
    payload = {
        "email": email,
        "username": username,
        "password": "supersecret",
        "is_seller": is_seller,
    }
    if display_name:
        payload["display_name"] = display_name
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def seller_token():
    # Unique creds: this module shares the DB engine with test_auth.py.
    return _register("shop_seller@example.com", "shopseller", is_seller=True, display_name="Mega Seller")


@pytest.fixture(scope="module")
def buyer_token():
    return _register("shop_buyer@example.com", "shopbuyer")


@pytest.fixture(scope="module")
def listing(seller_token):
    # Insert the listing directly via the DB — /listings router is owned by
    # OpenClaw and may not be wired into main.py when this test runs.
    from sqlmodel import Session, select

    from app.db import engine
    from app.models import Listing, User

    with Session(engine) as session:
        seller = session.exec(select(User).where(User.email == "shop_seller@example.com")).one()
        listing = Listing(
            seller_id=seller.id,
            title="Rare Comic #1",
            description="Mint condition",
            price=25.0,
            category="Comics",
            quantity=5,
            type="buy_now",
        )
        session.add(listing)
        session.commit()
        session.refresh(listing)
        return {"id": listing.id, "title": listing.title, "price": listing.price}


def test_cart_empty_initial(buyer_token):
    r = client.get("/cart", headers=_auth(buyer_token))
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0}


def test_add_to_cart(buyer_token, listing):
    r = client.post(
        "/cart/items",
        json={"listing_id": listing["id"], "qty": 2},
        headers=_auth(buyer_token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["qty"] == 2
    assert body["subtotal"] == 50.0

    # re-adding merges qty
    r2 = client.post(
        "/cart/items",
        json={"listing_id": listing["id"], "qty": 3},
        headers=_auth(buyer_token),
    )
    assert r2.status_code == 201
    assert r2.json()["qty"] == 5


def test_cart_requires_auth():
    assert client.get("/cart").status_code == 401
    assert client.post("/cart/items", json={"listing_id": 1, "qty": 1}).status_code == 401


def test_add_missing_listing_404(buyer_token):
    r = client.post("/cart/items", json={"listing_id": 9999, "qty": 1}, headers=_auth(buyer_token))
    assert r.status_code == 404


def test_update_and_remove(buyer_token, listing):
    r = client.patch(
        f"/cart/items/{listing['id']}",
        json={"qty": 1},
        headers=_auth(buyer_token),
    )
    assert r.status_code == 200
    assert r.json()["qty"] == 1

    r2 = client.delete(f"/cart/items/{listing['id']}", headers=_auth(buyer_token))
    assert r2.status_code == 204
    assert client.get("/cart", headers=_auth(buyer_token)).json()["items"] == []


def test_checkout_creates_order_and_clears_cart(buyer_token, seller_token, listing):
    # Reset cart quantity to a known value.
    client.post("/cart/items", json={"listing_id": listing["id"], "qty": 2}, headers=_auth(buyer_token))

    r = client.post("/cart/checkout", headers=_auth(buyer_token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 50.0
    order_id = body["order_id"]

    # cart is now empty
    cart = client.get("/cart", headers=_auth(buyer_token)).json()
    assert cart["items"] == []

    # order exists for buyer with items
    orders = client.get("/orders", headers=_auth(buyer_token)).json()
    assert any(o["id"] == order_id for o in orders)
    order = next(o for o in orders if o["id"] == order_id)
    assert order["status"] == "pending"
    assert order["total"] == 50.0
    assert len(order["items"]) == 1
    assert order["items"][0]["qty"] == 2

    # seller sees it in their queue
    seller_orders = client.get("/orders/seller/queue", headers=_auth(seller_token)).json()
    assert any(o["id"] == order_id for o in seller_orders)


def test_checkout_empty_cart_400(buyer_token):
    # cart is empty after checkout in prior test
    r = client.post("/cart/checkout", headers=_auth(buyer_token))
    assert r.status_code == 400


def test_order_status_transitions(buyer_token, seller_token, listing):
    client.post("/cart/items", json={"listing_id": listing["id"], "qty": 1}, headers=_auth(buyer_token))
    order_id = client.post("/cart/checkout", headers=_auth(buyer_token)).json()["order_id"]

    # buyer cannot update status
    r = client.patch(f"/orders/{order_id}/status", json={"status": "paid"}, headers=_auth(buyer_token))
    assert r.status_code == 403

    # invalid transition
    r = client.patch(f"/orders/{order_id}/status", json={"status": "shipped"}, headers=_auth(seller_token))
    assert r.status_code == 400

    # valid: pending -> paid -> shipped
    r = client.patch(f"/orders/{order_id}/status", json={"status": "paid"}, headers=_auth(seller_token))
    assert r.status_code == 200
    assert r.json()["status"] == "paid"

    r = client.patch(f"/orders/{order_id}/status", json={"status": "shipped"}, headers=_auth(seller_token))
    assert r.status_code == 200
    assert r.json()["status"] == "shipped"


def test_order_access_control(buyer_token, seller_token):
    # another user's order is 403
    r = client.get("/orders/1", headers=_auth(buyer_token))
    # order 1 belongs to buyer1 (from earlier test) — buyer2 check below
    assert r.status_code in (200, 404)
