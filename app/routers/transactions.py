import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/transactions", tags=["transactions"])


def get_transaction_or_404(db: Session, transaction_id: int, user: models.User):
    transaction = db.get(models.Transaction, transaction_id)
    # Someone else's payment looks the same as a missing one
    if transaction is None or transaction.user_id != user.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


def ensure_category_exists(db: Session, category_id: int) -> None:
    if db.get(models.Category, category_id) is None:
        raise HTTPException(status_code=400, detail="Category does not exist")


@router.post("", response_model=schemas.TransactionOut, status_code=201)
def create_transaction(
    payload: schemas.TransactionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    ensure_category_exists(db, payload.category_id)
    transaction = models.Transaction(**payload.model_dump(), user_id=user.id)
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("", response_model=list[schemas.TransactionOut])
def list_transactions(
    month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    query = (
        select(models.Transaction)
        .where(models.Transaction.user_id == user.id)
        .order_by(models.Transaction.date.desc(), models.Transaction.id.desc())
    )
    if month:
        year, mon = map(int, month.split("-"))
        start = dt.date(year, mon, 1)
        end = dt.date(year + (mon == 12), mon % 12 + 1, 1)
        query = query.where(models.Transaction.date >= start, models.Transaction.date < end)
    return db.scalars(query).all()


@router.get("/{transaction_id}", response_model=schemas.TransactionOut)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return get_transaction_or_404(db, transaction_id, user)


@router.patch("/{transaction_id}", response_model=schemas.TransactionOut)
def update_transaction(
    transaction_id: int,
    payload: schemas.TransactionUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    transaction = get_transaction_or_404(db, transaction_id, user)
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes:
        ensure_category_exists(db, changes["category_id"])
    for field, value in changes.items():
        setattr(transaction, field, value)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    transaction = get_transaction_or_404(db, transaction_id, user)
    db.delete(transaction)
    db.commit()