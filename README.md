# Construction Quote API

A REST API that lets a contractor create priced construction quotes: a client,
line items (description, quantity, unit price), totals that are **always
computed on the server**, user accounts with JWT authentication, and a
printable PDF of every quote.

Built with **FastAPI + SQLAlchemy**, migrated with **Alembic**, tested with
**pytest**, packaged with **Docker** and deployed on **Render + Supabase
(PostgreSQL)**.

## Live demo

**API:** https://construction-quote-api.onrender.com
**Interactive docs (Swagger):** https://construction-quote-api.onrender.com/docs

Demo account (for the `/docs` "Authorize" button — login uses the OAuth2 form,
`username` is the email):

```
demo@quoteapi.dev / DemoPass123
```

Note: the free tier sleeps when idle, so the first request can take ~30 s.

## Tech stack

- **FastAPI** + **Pydantic v2** — request/response validation
- **SQLAlchemy 2.0** + **Alembic** — ORM and versioned migrations
- **PostgreSQL** in production (Supabase), SQLite for tests/local — same code,
  the database is chosen by the `DATABASE_URL` environment variable
- **JWT** auth (PyJWT) with **Argon2** password hashing (pwdlib)
- **fpdf2** — pure-Python PDF generation, no system dependencies
- **pytest** + **GitHub Actions** — 15 tests and a Docker build on every push
- **Docker** + docker-compose (app + PostgreSQL in one command)

## Run locally

Without Docker (SQLite):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

With Docker (app + PostgreSQL):

```bash
docker compose up --build
```

Then open the interactive docs at `http://127.0.0.1:8000/docs`.

Apply the database migrations (production / PostgreSQL):

```bash
alembic upgrade head
```

## API overview

| Method | Path               | Auth | Description                                     |
| ------ | ------------------ | ---- | ----------------------------------------------- |
| GET    | `/health`          | —    | Health check                                    |
| POST   | `/auth/register`   | —    | Create an account                               |
| POST   | `/auth/login`      | —    | Get a JWT access token                          |
| POST   | `/quotes`          | JWT  | Create a quote with its items                   |
| GET    | `/quotes`          | JWT  | List your quotes (`limit` / `offset` pagination) |
| GET    | `/quotes/{id}`     | JWT  | Read one of your quotes (404 if not yours)      |
| PATCH  | `/quotes/{id}`     | JWT  | Update fields and/or replace the items          |
| DELETE | `/quotes/{id}`     | JWT  | Delete one of your quotes                       |
| GET    | `/quotes/{id}/pdf` | JWT  | Download the quote as a PDF                     |

A quote has a client name, a title, a status (`draft` / `sent` / `approved`),
an optional note and its line items. Every quote belongs to exactly one user:
other users can't read, edit, delete or download it — they get a 404.

## How totals are calculated

The client only sends descriptions, quantities and unit prices. The server
computes each line total, the subtotal, the tax (`subtotal × tax_rate`, where
`tax_rate` is a fraction — `0.18` means 18%) and the grand total. Totals are
derived from the items on every read, so they can never drift out of sync,
and any total sent by the client is ignored.

## Tests

```bash
pytest -q
```

The suite (15 tests) covers registration and login rules, authentication
requirements, full quote CRUD, pagination, server-side total computation with
several tax rates, PDF generation, and per-user data isolation — including
that one user cannot read, patch, delete or download another user's quote.

## Project structure

```
app/
  main.py      FastAPI app and endpoints
  models.py    SQLAlchemy models (User, Quote, QuoteItem)
  schemas.py   Pydantic request/response schemas
  auth.py      Password hashing and JWT helpers
  database.py  Engine/session, DATABASE_URL from the environment
  pdf.py       Quote PDF rendering (fpdf2)
alembic/       Versioned database migrations
tests/         pytest suite (runs against a throwaway database)
Dockerfile, docker-compose.yml
```
