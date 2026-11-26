from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.importer import guess_category, parse_csv
from app.security import get_current_user

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/csv", response_model=schemas.ImportResult)
def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    try:
        rows, errors = parse_csv(file.file.read())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # This user's payments already in the database for the dates in this file
    existing = set()
    if rows:
        first = min(r["date"] for r in rows)
        last = max(r["date"] for r in rows)
        query = select(
            models.Transaction.date,
            models.Transaction.amount,
            models.Transaction.description,
        ).where(
            models.Transaction.user_id == user.id,
            models.Transaction.date >= first,
            models.Transaction.date <= last,
        )
        existing = {(d, a, desc) for d, a, desc in db.execute(query)}

    categories = {}

    def get_category(name: str) -> models.Category:
        if name not in categories:
            category = db.scalar(select(models.Category).where(models.Category.name == name))
            if category is None:
                category = models.Category(name=name)
                db.add(category)
                db.flush()
            categories[name] = category
        return categories[name]

    imported = skipped = 0
    for row in rows:
        key = (row["date"], row["amount"], row["description"])
        if key in existing:
            skipped += 1
            continue
        existing.add(key)
        category = get_category(guess_category(row["description"] or ""))
        db.add(
            models.Transaction(
                user_id=user.id,
                amount=row["amount"],
                date=row["date"],
                description=row["description"],
                payment_method=row["payment_method"],
                category_id=category.id,
            )
        )
        imported += 1

    db.commit()
    return schemas.ImportResult(
        imported=imported,
        skipped_duplicates=skipped,
        errors=[schemas.RowError(row=n, reason=r) for n, r in errors],
    )