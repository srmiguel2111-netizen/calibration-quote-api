from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class QuoteItemIn(BaseModel):
    description: str
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class QuoteCreate(BaseModel):
    title: str
    tax_rate: float = Field(default=0.18, ge=0, le=1)
    items: list[QuoteItemIn] = Field(min_length=1)


class QuoteItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    quantity: float
    unit_price: float
    line_total: float


class QuoteOut(BaseModel):
    id: int
    title: str
    tax_rate: float
    items: list[QuoteItemOut]
    subtotal: float
    tax_amount: float
    total: float
