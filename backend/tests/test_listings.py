"""Listings router tests: CRUD, filters, auth/ownership, buy-now flow."""
import os
import tempfile

# Throwaway SQLite per test session — set BEFORE importing app (same pattern as test_auth.py).
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from app.db import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Order, OrderItem  # noqa: E402
from app.routers.listings import router as listings_router  # noqa: E402

# main.py is wired by Hermes; include the router here so this slice is testable now.
if not any(getattr(r, "path", None) == "/listings" for r in app.routes):
    app.include_router(listings_router)

init_db()
client = TestClient(app)


def _auth(email: str, username: str, *, is_seller: bool = False, display_name: str | None = None) -> dict:
    body = {"email": email, "username": username, "password": "supersecret", "is_seller": is_seller}
    if display_name:
        body["display_name"] = display_name
    r = client.post("/auth/register", json=body)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create_listing(headers: dict, title: str = "Foil Charizard", category: str = "Trading Cards", **extra) -> dict:
    payload = {"title": title, "category": category, **extra}
    r = client.post("/listings", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_listings_require_auth():
    assert client.post("/listings", json={"title": "X", "category": "Toys"}).status_code == 401
    assert client.patch("/listings/1", json={"title": "X"}).status_code == 401
    assert client.delete("/listings/1").status_code == 401
    assert client.post("/listings/1/buy", json={"quantity": 1}).status_code == 401


def test_create_listing_requires_seller():
    buyer = _auth("list_buyer0@test.dev", "listbuyer0")
    r = client.post("/listings", json={"title": "Nope", "category": "Toys"}, headers=buyer)
    assert r.status_code == 403


def test_listing_crud_and_filters():
    seller = _auth("list_seller1@test.dev", "listseller1", is_seller=True)

    listing = _create_listing(
        seller,
        title="Foil Charizard PSA 10",
        category="Trading Cards",
        type="buy_now",
        price=49.99,
        quantity=3,
        images=["http://img/1.jpg", "http://img/2.jpg"],
        description="Mint condition",
    )
    assert listing["images"] == "http://img/1.jpg,http://img/2.jpg"
    assert listing["quantity"] == 3
    assert listing["type"] == "buy_now"

    # GET single
    r = client.get(f"/listings/{listing['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Foil Charizard PSA 10"

    # Filters
    assert any(l["id"] == listing["id"] for l in client.get("/listings", params={"category": "Trading Cards"}).json())
    assert all(l["id"] != listing["id"] for l in client.get("/listings", params={"category": "Sneakers"}).json())
    assert any(l["id"] == listing["id"] for l in client.get("/listings", params={"seller_id": listing["seller_id"]}).json())
    assert any(l["id"] == listing["id"] for l in client.get("/listings", params={"type": "buy_now"}).json())

    # PATCH
    r = client.patch(f"/listings/{listing['id']}", json={"price": 59.99, "quantity": 5}, headers=seller)
    assert r.status_code == 200, r.text
    assert r.json()["price"] == 59.99
    assert r.json()["quantity"] == 5
    assert client.patch(f"/listings/{listing['id']}", json={}, headers=seller).status_code == 400

    # DELETE
    assert client.delete(f"/listings/{listing['id']}", headers=seller).status_code == 204
    assert client.get(f"/listings/{listing['id']}").status_code == 404


def test_listing_ownership_and_404():
    seller_a = _auth("list_seller_a@test.dev", "listsellera", is_seller=True)
    seller_b = _auth("list_seller_b@test.dev", "listsellerb", is_seller=True)
    listing = _create_listing(seller_a, title="A's Card", category="Collectibles", type="buy_now", price=10.0)

    assert client.patch(f"/listings/{listing['id']}", json={"price": 1.0}, headers=seller_b).status_code == 403
    assert client.delete(f"/listings/{listing['id']}", headers=seller_b).status_code == 403
    assert client.get(f"/listings/{listing['id']}").status_code == 200

    assert client.get("/listings/99999").status_code == 404
    assert client.patch("/listings/99999", json={"price": 1.0}, headers=seller_a).status_code == 404
    assert client.delete("/listings/99999", headers=seller_a).status_code == 404


def test_buy_now_flow():
    seller = _auth("list_seller2@test.dev", "listseller2", is_seller=True)
    buyer = _auth("list_buyer1@test.dev", "listbuyer1")

    listing = _create_listing(seller, title="Buy Me", category="Toys", type="buy_now", price=20.0, quantity=3)

    # Buy 2 units
    r = client.post(f"/listings/{listing['id']}/buy", json={"quantity": 2}, headers=buyer)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["order_id"]
    assert body["total"] == 40.0
    assert body["status"] == "pending"

    # Quantity decremented
    assert client.get(f"/listings/{listing['id']}").json()["quantity"] == 1

    # Order + OrderItem persisted with the right shape
    with Session(engine) as s:
        order = s.get(Order, body["order_id"])
        assert order is not None
        assert order.buyer_id is not None
        assert order.seller_id == listing["seller_id"]
        assert order.total == 40.0
        assert order.status.value == "pending"
        item = s.exec(
            select(OrderItem).where(OrderItem.order_id == order.id)
        ).first()
        assert item is not None
        assert item.listing_id == listing["id"]
        assert item.title == "Buy Me"
        assert item.price == 20.0
        assert item.qty == 2

    # Buy remaining unit with default quantity
    r = client.post(f"/listings/{listing['id']}/buy", json={}, headers=buyer)
    assert r.status_code == 201, r.text
    assert client.get(f"/listings/{listing['id']}").json()["quantity"] == 0

    # Over-stock rejected
    r = client.post(f"/listings/{listing['id']}/buy", json={"quantity": 1}, headers=buyer)
    assert r.status_code == 400

    # Auction listings cannot be bought
    auction = _create_listing(seller, title="Auction Only", category="Toys", type="auction", start_price=5.0)
    r = client.post(f"/listings/{auction['id']}/buy", json={"quantity": 1}, headers=buyer)
    assert r.status_code == 400

    # Missing listing
    assert client.post("/listings/99999/buy", json={"quantity": 1}, headers=buyer).status_code == 404


def test_listing_validation_and_show_link():
    seller = _auth("list_seller3@test.dev", "listseller3", is_seller=True)
    # Bad category
    r = client.post("/listings", json={"title": "X", "category": "Nope"}, headers=seller)
    assert r.status_code == 422
    # Blank title
    r = client.post("/listings", json={"title": "   ", "category": "Toys"}, headers=seller)
    assert r.status_code == 422
    # Negative price
    r = client.post("/listings", json={"title": "X", "category": "Toys", "price": -1}, headers=seller)
    assert r.status_code == 422
    # Nonexistent show
    r = client.post("/listings", json={"title": "X", "category": "Toys", "show_id": 99999}, headers=seller)
    assert r.status_code == 404
