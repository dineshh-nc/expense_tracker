import datetime as dt
from decimal import Decimal

from sqlalchemy import select

from app import models
from app.database import SessionLocal

CATEGORIES = ["Food", "Rent", "Travel", "Bills", "Shopping"]

# (date, amount, category, description, payment method)
PAYMENTS = [
    ("2026-10-01", "12000.00", "Rent", "October rent", "UPI"),
    ("2026-10-05", "850.00", "Bills", "Electricity bill", "UPI"),
    ("2026-10-09", "420.00", "Food", "Dinner out", "Card"),
    ("2026-10-14", "1800.00", "Shopping", "Shoes", "Card"),
    ("2026-10-20", "650.00", "Travel", "Cab rides", "UPI"),
    ("2026-10-27", "300.00", "Food", "Groceries", "Cash"),
    ("2026-11-01", "12000.00", "Rent", "November rent", "UPI"),
    ("2026-11-04", "900.00", "Bills", "Internet bill", "UPI"),
    ("2026-11-08", "560.00", "Food", "Groceries", "UPI"),
    ("2026-11-12", "2200.00", "Travel", "Train tickets", "Card"),
    ("2026-11-16", "1500.00", "Shopping", "Clothes", "Card"),
    ("2026-11-19", "380.00", "Food", "Dinner out", "Cash"),
]

db = SessionLocal()

already = db.scalar(
    select(models.Transaction).where(models.Transaction.description.like("%(sample)"))
)
if already:
    print("Sample data already added. Nothing to do.")
    raise SystemExit

categories = {}
for name in CATEGORIES:
    category = db.scalar(select(models.Category).where(models.Category.name == name))
    if category is None:
        category = models.Category(name=name)
        db.add(category)
        db.flush()
    categories[name] = category

for date, amount, category_name, description, method in PAYMENTS:
    db.add(
        models.Transaction(
            amount=Decimal(amount),
            date=dt.date.fromisoformat(date),
            description=f"{description} (sample)",
            payment_method=method,
            category_id=categories[category_name].id,
        )
    )

db.commit()
print("Added sample categories and payments.")