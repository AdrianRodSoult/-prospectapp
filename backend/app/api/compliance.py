from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import SuppressionEntry, User

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


class SuppressionCreate(BaseModel):
    value: str
    reason: str | None = None


@router.get("/suppression")
def list_suppression(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(SuppressionEntry).all()


@router.post("/suppression")
def add_suppression(payload: SuppressionCreate, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    entry = SuppressionEntry(value=payload.value.lower().strip(), reason=payload.reason)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/suppression/{entry_id}")
def remove_suppression(entry_id: str, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    db.query(SuppressionEntry).filter(SuppressionEntry.id == entry_id).delete()
    db.commit()
    return {"ok": True}
