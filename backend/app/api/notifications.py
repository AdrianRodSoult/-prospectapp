from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Notification, User
from app.schemas.schemas import NotificationsResponse

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationsResponse)
def list_notifications(limit: int = 20, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    limit = max(1, min(limit, 50))
    items = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.read.is_(False)
    ).count()
    return NotificationsResponse(items=items, unread_count=unread_count)


@router.post("/{notification_id}/read")
def mark_as_read(notification_id: str, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    notif = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == current_user.id
    ).first()
    if not notif:
        raise HTTPException(404, "Notificación no encontrada")
    notif.read = True
    db.commit()
    return {"ok": True}


@router.post("/read-all")
def mark_all_as_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.read.is_(False)
    ).update({"read": True})
    db.commit()
    return {"ok": True}
