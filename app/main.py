from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from . import models, schemas
from .auth import create_access_token, get_current_user, hash_password, verify_password
from .database import Base, engine, get_db
from .pdf import build_quote_pdf

# Local/dev convenience only. Production schema is managed by Alembic
# migrations (see alembic/); create_all never alters an existing schema.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Construction Quote API", version="1.0.0")


def quote_out(quote: models.Quote) -> schemas.QuoteOut:
    return schemas.QuoteOut(
        id=quote.id,
        client_name=quote.client_name,
        title=quote.title,
        status=quote.status,
        tax_rate=quote.tax_rate,
        notes=quote.notes,
        items=[
            schemas.QuoteItemOut(
                id=item.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                position=item.position,
                line_total=item.line_total,
            )
            for item in quote.items
        ],
        subtotal=quote.subtotal,
        tax_amount=quote.tax_amount,
        total=quote.total,
        created_at=quote.created_at,
        updated_at=quote.updated_at,
    )


def _items_from_payload(items_in) -> list[models.QuoteItem]:
    return [
        models.QuoteItem(
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            position=position,
        )
        for position, item in enumerate(items_in)
    ]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        email=payload.email, hashed_password=hash_password(payload.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=schemas.Token)
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return schemas.Token(access_token=create_access_token(user.id))


@app.post("/quotes", response_model=schemas.QuoteOut, status_code=status.HTTP_201_CREATED)
def create_quote(
    payload: schemas.QuoteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    quote = models.Quote(
        title=payload.title,
        client_name=payload.client_name,
        status=payload.status,
        tax_rate=payload.tax_rate,
        notes=payload.notes,
        user_id=current_user.id,
    )
    quote.items = _items_from_payload(payload.items)
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote_out(quote)


@app.get("/quotes", response_model=list[schemas.QuoteOut])
def list_quotes(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    quotes = (
        db.query(models.Quote)
        .filter(models.Quote.user_id == current_user.id)
        .order_by(models.Quote.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [quote_out(q) for q in quotes]


def _get_own_quote(db: Session, quote_id: int, user_id: int) -> models.Quote:
    quote = (
        db.query(models.Quote)
        .filter(models.Quote.id == quote_id, models.Quote.user_id == user_id)
        .first()
    )
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote


@app.get("/quotes/{quote_id}", response_model=schemas.QuoteOut)
def get_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return quote_out(_get_own_quote(db, quote_id, current_user.id))


@app.patch("/quotes/{quote_id}", response_model=schemas.QuoteOut)
def patch_quote(
    quote_id: int,
    payload: schemas.QuotePatch,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    quote = _get_own_quote(db, quote_id, current_user.id)
    updates = payload.model_dump(exclude_unset=True)
    new_items = updates.pop("items", None)
    for field, value in updates.items():
        setattr(quote, field, value)
    if new_items is not None:
        quote.items = _items_from_payload(payload.items)
    db.commit()
    db.refresh(quote)
    return quote_out(quote)


@app.delete("/quotes/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    quote = _get_own_quote(db, quote_id, current_user.id)
    db.delete(quote)
    db.commit()
    return None


@app.get("/quotes/{quote_id}/pdf")
def get_quote_pdf(
    quote_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    quote = _get_own_quote(db, quote_id, current_user.id)
    content = build_quote_pdf(quote)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="quote-{quote.id}.pdf"'
        },
    )
