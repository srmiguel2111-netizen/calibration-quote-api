from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

QuoteStatus = Literal["draft", "sent", "approved"]


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class QuoteItemIn(BaseModel):
    description: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class QuoteCreate(BaseModel):
    title: str
    client_name: str = ""
    status: QuoteStatus = "draft"
    tax_rate: float = Field(default=0.18, ge=0, le=1)
    notes: Optional[str] = None
    items: list[QuoteItemIn] = Field(min_length=1)


class QuotePatch(BaseModel):
    title: Optional[str] = None
    client_name: Optional[str] = None
    status: Optional[QuoteStatus] = None
    tax_rate: Optional[float] = Field(default=None, ge=0, le=1)
    notes: Optional[str] = None
    items: Optional[list[QuoteItemIn]] = Field(default=None, min_length=1)


class QuoteItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    quantity: float
    unit_price: float
    position: int
    line_total: float


class QuoteOut(BaseModel):
    id: int
    client_name: str
    title: str
    status: str
    tax_rate: float
    notes: Optional[str]
    items: list[QuoteItemOut]
    subtotal: float
    tax_amount: float
    total: float
    created_at: datetime
    updated_at: datetime
