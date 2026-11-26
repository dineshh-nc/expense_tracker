from app.security import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=schemas.CategoryOut, status_code=201)
def create_category(
    payload: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    exists = db.scalar(select(models.Category).where(models.Category.name == payload.name))
    if exists:
        raise HTTPException(status_code=409, detail="Category already exists")
    category = models.Category(name=payload.name)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("", response_model=list[schemas.CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return db.scalars(select(models.Category).order_by(models.Category.name)).all()