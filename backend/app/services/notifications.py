"""
Creación centralizada de notificaciones, para no repetir la lógica en
cada endpoint que las dispara.
"""
from sqlalchemy.orm import Session

from app.models.models import Notification


def notify_high_priority_lead(db: Session, user_id: str, business_id: str, business_name: str) -> None:
    db.add(Notification(
        user_id=user_id, business_id=business_id, type="high_priority_lead",
        message=f"Nuevo lead de prioridad alta: {business_name}",
    ))


def notify_business_responded(db: Session, user_id: str, business_id: str, business_name: str) -> None:
    db.add(Notification(
        user_id=user_id, business_id=business_id, type="business_responded",
        message=f"{business_name} ha respondido",
    ))
