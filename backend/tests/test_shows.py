"""Shows router tests: discovery feed, filters, search, CRUD, auth + ownership."""
import os
import tempfile

# Throwaway SQLite per test session — set BEFORE importing app (same pattern as test_auth.py).
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.routers.shows import router as shows_router  # noqa: E402

# main.py is wired by Hermes; include the router here so this slice is testable now.
if not any(getattr(r, "path", None) == "/shows" for r in app.routes):
    app.include_router(shows_router)

init_db()
client = TestClient(app)


def _auth(email: str, username: str, *, is_seller: bool = False, display_name: str | None = None) -> dict:
    body = {"email": email, "username": username, "password": "supersecret", "is_seller": is_seller}
    if display_name:
        body["display_name"] = display_name
    r = client.post("/auth/register", json=body)
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _create_show(headers: dict, title: str = "Vintage Cards Live", category: str = "Trading Cards", **extra) -> dict:
    r = client.post("/shows", json={"title": title, "category": category, **extra}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_shows_require_auth():
    assert client.post("/shows", json={"title": "X", "category": "Toys"}).status_code == 401
    assert client.patch("/shows/1", json={"title": "X"}).status_code == 401
    assert client.delete("/shows/1").status_code == 401


def test_create_show_requires_seller():
    buyer = _auth("shows_buyer1@test.dev", "showsbuyer1")
    r = client.post("/shows", json={"title": "Nope", "category": "Toys"}, headers=buyer)
    assert r.status_code == 403


def test_show_crud_and_feed():
    seller = _auth("shows_seller1@test.dev", "showsseller1", is_seller=True, display_name="Card King")
    show = _create_show(seller, title="Vintage Cards Live", category="Trading Cards",
                        scheduled_at="2026-09-01T18:00:00Z", thumbnail_url="http://img/t.jpg")

    # GET single show: enriched with seller display_name + viewer_count
    r = client.get(f"/shows/{show['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["seller_display_name"] == "Card King"
    assert body["viewer_count"] == 0
    assert body["status"] == "scheduled"

    # Feed: default = live + upcoming (scheduled), enriched
    r = client.get("/shows")
    assert r.status_code == 200
    assert any(s["title"] == "Vintage Cards Live" and s["seller_display_name"] == "Card King" for s in r.json())

    # Category filter
    r = client.get("/shows", params={"category": "Trading Cards"})
    assert any(s["id"] == show["id"] for s in r.json())
    r = client.get("/shows", params={"category": "Sneakers"})
    assert all(s["id"] != show["id"] for s in r.json())

    # Search (case-insensitive)
    r = client.get("/shows", params={"q": "vintage"})
    assert any(s["id"] == show["id"] for s in r.json())
    r = client.get("/shows", params={"q": "zzz-no-match"})
    assert all(s["id"] != show["id"] for s in r.json())

    # Status filter: not live yet
    r = client.get("/shows", params={"status": "live"})
    assert all(s["id"] != show["id"] for s in r.json())

    # PATCH: go live + change title
    r = client.patch(f"/shows/{show['id']}", json={"status": "live", "title": "Vintage Cards NOW"}, headers=seller)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "live"
    assert r.json()["title"] == "Vintage Cards NOW"

    r = client.get("/shows", params={"status": "live"})
    assert any(s["id"] == show["id"] for s in r.json())

    # PATCH validation: bad category / bad status / empty body
    assert client.patch(f"/shows/{show['id']}", json={"category": "Nope"}, headers=seller).status_code == 422
    assert client.patch(f"/shows/{show['id']}", json={"status": "bogus"}, headers=seller).status_code == 422
    assert client.patch(f"/shows/{show['id']}", json={}, headers=seller).status_code == 400

    # DELETE then 404
    assert client.delete(f"/shows/{show['id']}", headers=seller).status_code == 204
    assert client.get(f"/shows/{show['id']}").status_code == 404


def test_show_ownership_and_404():
    seller_a = _auth("shows_seller_a@test.dev", "showssellera", is_seller=True)
    seller_b = _auth("shows_seller_b@test.dev", "showssellerb", is_seller=True)
    show = _create_show(seller_a, title="A's Show", category="Comics")

    # Other seller cannot patch/delete
    assert client.patch(f"/shows/{show['id']}", json={"title": "Hijack"}, headers=seller_b).status_code == 403
    assert client.delete(f"/shows/{show['id']}", headers=seller_b).status_code == 403

    # Owner can still see/delete it
    assert client.get(f"/shows/{show['id']}").status_code == 200
    assert client.delete(f"/shows/{show['id']}", headers=seller_a).status_code == 204

    # Missing show
    assert client.get("/shows/99999").status_code == 404
    assert client.patch("/shows/99999", json={"title": "X"}, headers=seller_a).status_code == 404
    assert client.delete("/shows/99999", headers=seller_a).status_code == 404


def test_show_validation():
    seller = _auth("shows_seller2@test.dev", "showsseller2", is_seller=True)
    assert client.post("/shows", json={"title": "", "category": "Toys"}, headers=seller).status_code == 422
    assert client.post("/shows", json={"title": "X", "category": "Unknown"}, headers=seller).status_code == 422
    assert client.post("/shows", json={"category": "Toys"}, headers=seller).status_code == 422
