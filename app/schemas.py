import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)


class CategoryOut(CategoryCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    date: dt.date
    description: str | None = Field(default=None, max_length=255)
    payment_method: str | None = Field(default=None, max_length=30)
    category_id: int


class TransactionUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    date: dt.date | None = None
    description: str | None = Field(default=None, max_length=255)
    payment_method: str | None = Field(default=None, max_length=30)
    category_id: int | None = None


class TransactionOut(BaseModel):
    id: int
    amount: Decimal
    date: dt.date
    description: str | None
    payment_method: str | None
    category_id: int
    created_at: dt.datetime
    model_config = ConfigDict(from_attributes=True)


class CategoryTotal(BaseModel):
    category: str
    total: Decimal
    count: int
    percent: float


class MonthlyReport(BaseModel):
    month: str
    total: Decimal
    payment_count: int
    by_category: list[CategoryTotal]


class DailyTotal(BaseModel):
    date: dt.date
    total: Decimal


class DailyReport(BaseModel):
    month: str
    days: list[DailyTotal]


class MonthComparison(BaseModel):
    month: str
    previous_month: str
    current_total: Decimal
    previous_total: Decimal
    difference: Decimal
    percent_change: float | None


class RowError(BaseModel):
    row: int
    reason: str


class ImportResult(BaseModel):
    imported: int
    skipped_duplicates: int
    errors: list[RowError]

class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    id: int
    email: str
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
