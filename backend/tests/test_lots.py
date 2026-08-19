"""Lots router tests: create + list lots with ownership and type checks.

Unique creds: this module shares the SQLite engine with the other test
modules (same temp-file env pattern as test_cart_orders.py).
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
    return _register("lots_seller@example.com", "lotsseller", is_seller=True, display_name="Lot Seller")


@pytest.fixture(scope="module")
def other_seller_token():
    return _register("lots_other@example.com", "lotsother", is_seller=True, display_name="Other Seller")


@pytest.fixture(scope="module")
def buyer_token():
    return _register("lots_buyer@example.com", "lotsbuyer")


@pytest.fixture(scope="module")
def show(seller_token):
    r = client.post(
        "/shows",
        json={"title": "Lot Show", "category": "Sneakers"},
        headers=_auth(seller_token),
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def auction_listing(seller_token):
    r = client.post(
        "/listings",
        json={
            "title": "Auction Card",
            "category": "Trading Cards",
            "type": "auction",
            "start_price": 10.0,
            "increment": 2.0,
        },
        headers=_auth(seller_token),
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def buy_now_listing(seller_token):
    r = client.post(
        "/listings",
        json={
            "title": "Fixed Item",
            "category": "Comics",
            "type": "buy_now",
            "price": 5.0,
            "quantity": 3,
        },
        headers=_auth(seller_token),
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def other_listing(other_seller_token):
    r = client.post(
        "/listings",
        json={
            "title": "Their Auction",
            "category": "Toys",
            "type": "auction",
            "start_price": 1.0,
            "increment": 1.0,
        },
        headers=_auth(other_seller_token),
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_list_lots_empty(show, buyer_token):
    r = client.get(f"/shows/{show['id']}/lots", headers=_auth(buyer_token))
    assert r.status_code == 200
    assert r.json() == []


def test_create_lot_success(show, auction_listing, seller_token):
    r = client.post(
        f"/shows/{show['id']}/lots",
        json={"listing_id": auction_listing["id"]},
        headers=_auth(seller_token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["listing_id"] == auction_listing["id"]
    assert body["status"] == "pending"
    assert body["order_index"] == 0


def test_lots_ordered_after_second(show, auction_listing, seller_token):
    r = client.post(
        f"/shows/{show['id']}/lots",
        json={"listing_id": auction_listing["id"]},
        headers=_auth(seller_token),
    )
    assert r.status_code == 201
    assert r.json()["order_index"] == 1

    lots = client.get(f"/shows/{show['id']}/lots").json()
    assert [l["order_index"] for l in lots] == [0, 1]


def test_create_lot_requires_seller(show, auction_listing, buyer_token):
    r = client.post(
        f"/shows/{show['id']}/lots",
        json={"listing_id": auction_listing["id"]},
        headers=_auth(buyer_token),
    )
    assert r.status_code == 403


def test_create_lot_requires_auth(show, auction_listing):
    r = client.post(f"/shows/{show['id']}/lots", json={"listing_id": auction_listing["id"]})
    assert r.status_code == 401


def test_create_lot_ownership_403(show, other_listing, other_seller_token):
    # Other seller's listing on my show -> 403 (listing belongs to another seller)
    r = client.post(
        f"/shows/{show['id']}/lots",
        json={"listing_id": other_listing["id"]},
        headers=_auth(other_seller_token),
    )
    assert r.status_code == 403


def test_create_lot_non_owner_show_403(show, auction_listing, other_seller_token):
    r = client.post(
        f"/shows/{show['id']}/lots",
        json={"listing_id": auction_listing["id"]},
        headers=_auth(other_seller_token),
    )
    assert r.status_code == 403


def test_create_lot_rejects_buy_now(show, buy_now_listing, seller_token):
    r = client.post(
        f"/shows/{show['id']}/lots",
        json={"listing_id": buy_now_listing["id"]},
        headers=_auth(seller_token),
    )
    assert r.status_code == 400


def test_create_lot_missing_listing_404(show, seller_token):
    r = client.post(
        f"/shows/{show['id']}/lots",
        json={"listing_id": 99999},
        headers=_auth(seller_token),
    )
    assert r.status_code == 404


def test_create_lot_missing_show_404(auction_listing, seller_token):
    r = client.post(
        "/shows/99999/lots",
        json={"listing_id": auction_listing["id"]},
        headers=_auth(seller_token),
    )
    assert r.status_code == 404


def test_list_lots_missing_show_404():
    assert client.get("/shows/99999/lots").status_code == 404
