import os
import tempfile

# Point the app at a throwaway database before importing it.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def register_and_login(email: str) -> str:
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    r = client.post(
        "/auth/login", data={"username": email, "password": "password123"}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_rejects_duplicate_email():
    client.post(
        "/auth/register", json={"email": "dup@example.com", "password": "password123"}
    )
    r = client.post(
        "/auth/register", json={"email": "dup@example.com", "password": "password123"}
    )
    assert r.status_code == 400


def test_quotes_require_authentication():
    assert client.get("/quotes").status_code == 401
    assert (
        client.post("/quotes", json={"title": "x", "items": []}).status_code == 401
    )


def test_create_quote_computes_totals_on_the_server():
    token = register_and_login("builder@example.com")
    payload = {
        "title": "Bathroom remodel",
        # A client-supplied total must be ignored: totals are server-computed.
        "total": 1,
        "items": [
            {"description": "Demolition", "quantity": 2, "unit_price": 100},
            {"description": "Tiles", "quantity": 1, "unit_price": 50},
        ],
    }
    r = client.post("/quotes", json=payload, headers=auth(token))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["subtotal"] == 250.0
    assert body["tax_amount"] == 45.0  # default 18% tax rate
    assert body["total"] == 295.0
    assert body["items"][0]["line_total"] == 200.0


def test_users_only_see_their_own_quotes():
    token_a = register_and_login("owner@example.com")
    token_b = register_and_login("intruder@example.com")
    r = client.post(
        "/quotes",
        json={
            "title": "Kitchen",
            "items": [{"description": "Cabinets", "quantity": 1, "unit_price": 900}],
        },
        headers=auth(token_a),
    )
    quote_id = r.json()["id"]

    # The other user's list is empty and the quote itself is invisible (404).
    assert client.get("/quotes", headers=auth(token_b)).json() == []
    assert client.get(f"/quotes/{quote_id}", headers=auth(token_b)).status_code == 404
    assert client.delete(f"/quotes/{quote_id}", headers=auth(token_b)).status_code == 404

    # The owner can read and delete it.
    assert client.get(f"/quotes/{quote_id}", headers=auth(token_a)).status_code == 200
    assert client.delete(f"/quotes/{quote_id}", headers=auth(token_a)).status_code == 204
    assert client.get(f"/quotes/{quote_id}", headers=auth(token_a)).status_code == 404
