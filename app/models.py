from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    quotes = relationship("Quote", back_populates="owner", cascade="all, delete-orphan")


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    tax_rate = Column(Float, nullable=False, default=0.18)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="quotes")
    items = relationship(
        "QuoteItem", back_populates="quote", cascade="all, delete-orphan"
    )

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
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)

    quote = relationship("Quote", back_populates="items")

    @property
    def line_total(self) -> float:
        return round(self.quantity * self.unit_price, 2)
