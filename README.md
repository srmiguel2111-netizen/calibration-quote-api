# Construction Quote API

Calibration build — a small FastAPI service that turns construction line items
into priced quotes, with JWT authentication and totals that are always
computed on the server.

## Stack

- **FastAPI** + **SQLAlchemy 2.0** (SQLite for this calibration build;
  the database URL is environment-driven, PostgreSQL in Project 1)
- **JWT** auth (PyJWT) with Argon2 password hashing (pwdlib)
- **pytest** + FastAPI `TestClient`

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive docs at `http://127.0.0.1:8000/docs`.

## Endpoints

| Method | Path            | Auth | Description                                  |
| ------ | --------------- | ---- | -------------------------------------------- |
| POST   | `/auth/register` | —    | Create an account                            |
| POST   | `/auth/login`    | —    | Get a JWT access token                       |
| POST   | `/quotes`        | JWT  | Create a quote; totals computed server-side  |
| GET    | `/quotes`        | JWT  | List your own quotes                         |
| GET    | `/quotes/{id}`   | JWT  | Read one of your quotes (404 if not yours)   |
| DELETE | `/quotes/{id}`   | JWT  | Delete one of your quotes                    |
| GET    | `/health`        | —    | Health check                                 |

Quote items carry `quantity` and `unit_price`; the API returns `subtotal`,
`tax_amount` (default 18%) and `total`. Any total sent by the client is
ignored by design.

## Tests

```bash
pytest -q
```

Covers registration, duplicate emails, authentication requirements,
server-side total computation and per-user data isolation.
