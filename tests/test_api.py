import os
import tempfile

# Point the app at a throwaway database before importing it.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-0123456789"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def register_and_login(email: str) -> str:
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201, r.text
    r = client.post("/auth/login", data={"username": email, "password": "password123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_quote(token: str, **overrides) -> dict:
    payload = {
        "title": "Bathroom remodel",
        "client_name": "Mrs. Perez",
        "items": [
            {"description": "Demolition", "quantity": 2, "unit_price": 100},
            {"description": "Tiles", "quantity": 1, "unit_price": 50},
        ],
    }
    payload.update(overrides)
    r = client.post("/quotes", json=payload, headers=auth(token))
    assert r.status_code == 201, r.text
    return r.json()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_register_rejects_duplicate_email():
    client.post(
        "/auth/register", json={"email": "dup@example.com", "password": "password123"}
    )
    r = client.post(
        "/auth/register", json={"email": "dup@example.com", "password": "password123"}
    )
    assert r.status_code == 400


def test_register_rejects_short_password():
    r = client.post(
        "/auth/register", json={"email": "short@example.com", "password": "short"}
    )
    assert r.status_code == 422


def test_login_rejects_wrong_password():
    client.post(
        "/auth/register", json={"email": "wp@example.com", "password": "password123"}
    )
    r = client.post(
        "/auth/login", data={"username": "wp@example.com", "password": "wrong-password"}
    )
    assert r.status_code == 401


def test_quotes_require_authentication():
    assert client.get("/quotes").status_code == 401
    assert client.post("/quotes", json={"title": "x", "items": []}).status_code == 401


def test_create_quote_computes_totals_on_the_server():
    token = register_and_login("builder@example.com")
    # A client-supplied total must be ignored: totals are server-computed.
    body = make_quote(token, total=1)
    assert body["subtotal"] == 250.0
    assert body["tax_amount"] == 45.0  # default 18% tax rate
    assert body["total"] == 295.0
    assert body["items"][0]["line_total"] == 200.0
    assert body["client_name"] == "Mrs. Perez"
    assert body["status"] == "draft"


def test_create_quote_with_custom_tax_rate():
    token = register_and_login("tax@example.com")
    body = make_quote(token, tax_rate=0.10)
    assert body["subtotal"] == 250.0
    assert body["tax_amount"] == 25.0
    assert body["total"] == 275.0


def test_create_quote_with_zero_tax():
    token = register_and_login("notax@example.com")
    body = make_quote(token, tax_rate=0)
    assert body["tax_amount"] == 0.0
    assert body["total"] == body["subtotal"]


def test_create_quote_rejects_empty_items():
    token = register_and_login("empty@example.com")
    r = client.post(
        "/quotes", json={"title": "Empty", "items": []}, headers=auth(token)
    )
    assert r.status_code == 422


def test_get_quote_detail():
    token = register_and_login("detail@example.com")
    created = make_quote(token)
    r = client.get(f"/quotes/{created['id']}", headers=auth(token))
    assert r.status_code == 200
    assert r.json()["title"] == "Bathroom remodel"
    assert len(r.json()["items"]) == 2


def test_patch_quote_updates_fields_and_recomputes_totals():
    token = register_and_login("patch@example.com")
    created = make_quote(token)
    r = client.patch(
        f"/quotes/{created['id']}",
        json={"status": "sent", "title": "Bathroom remodel v2"},
        headers=auth(token),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "sent"
    assert r.json()["title"] == "Bathroom remodel v2"

    # Replacing the items recomputes every total.
    r = client.patch(
        f"/quotes/{created['id']}",
        json={"items": [{"description": "Labor", "quantity": 3, "unit_price": 80}]},
        headers=auth(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["subtotal"] == 240.0
    assert body["total"] == 283.2


def test_list_quotes_pagination():
    token = register_and_login("pages@example.com")
    for i in range(3):
        make_quote(token, title=f"Job {i}")
    page1 = client.get("/quotes?limit=2&offset=0", headers=auth(token)).json()
    page2 = client.get("/quotes?limit=2&offset=2", headers=auth(token)).json()
    assert len(page1) == 2
    assert len(page2) == 1
    assert page1[0]["id"] != page2[0]["id"]


def test_users_only_see_their_own_quotes():
    token_a = register_and_login("owner@example.com")
    token_b = register_and_login("intruder@example.com")
    created = make_quote(token_a, title="Kitchen")
    quote_id = created["id"]

    assert client.get("/quotes", headers=auth(token_b)).json() == []
    assert client.get(f"/quotes/{quote_id}", headers=auth(token_b)).status_code == 404
    assert (
        client.patch(
            f"/quotes/{quote_id}", json={"title": "Hijack"}, headers=auth(token_b)
        ).status_code
        == 404
    )
    assert client.delete(f"/quotes/{quote_id}", headers=auth(token_b)).status_code == 404

    assert client.get(f"/quotes/{quote_id}", headers=auth(token_a)).status_code == 200
    assert client.delete(f"/quotes/{quote_id}", headers=auth(token_a)).status_code == 204
    assert client.get(f"/quotes/{quote_id}", headers=auth(token_a)).status_code == 404


def test_pdf_for_owner_returns_a_real_pdf():
    token = register_and_login("pdf@example.com")
    created = make_quote(token)
    r = client.get(f"/quotes/{created['id']}/pdf", headers=auth(token))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content.startswith(b"%PDF")
    assert f"quote-{created['id']}.pdf" in r.headers["content-disposition"]


def test_pdf_for_other_user_is_404():
    token_a = register_and_login("pdf-owner@example.com")
    token_b = register_and_login("pdf-intruder@example.com")
    created = make_quote(token_a)
    r = client.get(f"/quotes/{created['id']}/pdf", headers=auth(token_b))
    assert r.status_code == 404
