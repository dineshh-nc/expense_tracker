import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


def month_range(month: str) -> tuple[dt.date, dt.date]:
    year, mon = map(int, month.split("-"))
    start = dt.date(year, mon, 1)
    end = dt.date(year + (mon == 12), mon % 12 + 1, 1)  # first day of next month
    return start, end


def month_total(db: Session, user_id: int, start: dt.date, end: dt.date):
    return db.scalar(
        select(func.coalesce(func.sum(models.Transaction.amount), 0)).where(
            models.Transaction.user_id == user_id,
            models.Transaction.date >= start,
            models.Transaction.date < end,
        )
    )


@router.get("/monthly", response_model=schemas.MonthlyReport)
def monthly_report(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    start, end = month_range(month)
    in_month = (
        models.Transaction.user_id == user.id,
        models.Transaction.date >= start,
        models.Transaction.date < end,
    )

    total, count = db.execute(
        select(
            func.coalesce(func.sum(models.Transaction.amount), 0),
            func.count(models.Transaction.id),
        ).where(*in_month)
    ).one()

    rows = db.execute(
        select(
            models.Category.name,
            func.sum(models.Transaction.amount),
            func.count(models.Transaction.id),
        )
        .join(models.Category, models.Transaction.category_id == models.Category.id)
        .where(*in_month)
        .group_by(models.Category.name)
        .order_by(func.sum(models.Transaction.amount).desc())
    ).all()

    by_category = [
        schemas.CategoryTotal(
            category=name,
            total=cat_total,
            count=cat_count,
            percent=round(float(cat_total / total * 100), 1) if total else 0.0,
        )
        for name, cat_total, cat_count in rows
    ]

    return schemas.MonthlyReport(
        month=month, total=total, payment_count=count, by_category=by_category
    )


@router.get("/daily", response_model=schemas.DailyReport)
def daily_report(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    start, end = month_range(month)
    rows = db.execute(
        select(models.Transaction.date, func.sum(models.Transaction.amount))
        .where(
            models.Transaction.user_id == user.id,
            models.Transaction.date >= start,
            models.Transaction.date < end,
        )
        .group_by(models.Transaction.date)
        .order_by(models.Transaction.date)
    ).all()
    return schemas.DailyReport(
        month=month,
        days=[schemas.DailyTotal(date=day, total=total) for day, total in rows],
    )


@router.get("/compare", response_model=schemas.MonthComparison)
def compare_months(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    start, end = month_range(month)
    prev_start = (start - dt.timedelta(days=1)).replace(day=1)  # first day of last month
    current = month_total(db, user.id, start, end)
    previous = month_total(db, user.id, prev_start, start)
    percent = round(float((current - previous) / previous * 100), 1) if previous else None
    return schemas.MonthComparison(
        month=month,
        previous_month=prev_start.strftime("%Y-%m"),
        current_total=current,
        previous_total=previous,
        difference=current - previous,
        percent_change=percent,
    )