from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    quotes = relationship("Quote", back_populates="owner", cascade="all, delete-orphan")


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_name = Column(String, nullable=False, default="")
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft")
    tax_rate = Column(Float, nullable=False, default=0.18)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    owner = relationship("User", back_populates="quotes")
    items = relationship(
        "QuoteItem",
        back_populates="quote",
        cascade="all, delete-orphan",
        order_by="QuoteItem.position",
    )

    # Totals are always derived from the items; they are never stored as an
    # editable source of truth.
    @property
    def subtotal(self) -> float:
        return round(sum(item.quantity * item.unit_price for item in self.items), 2)

    @property
    def tax_amount(self) -> float:
        return round(self.subtotal * self.tax_rate, 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax_amount, 2)


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(
        Integer, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
    )
    description = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    position = Column(Integer, nullable=False, default=0)

    quote = relationship("Quote", back_populates="items")

    @property
    def line_total(self) -> float:
        return round(self.quantity * self.unit_price, 2)
