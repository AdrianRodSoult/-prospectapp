import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Business, User, AuditLog

router = APIRouter(prefix="/api/export", tags=["export"])

COLUMNS = ["name", "category", "address", "city", "phone_intl", "website_url",
           "rating", "review_count", "crm_stage", "whatsapp_status"]


@router.get("/csv")
def export_csv(search_id: str | None = None, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    q = db.query(Business)
    if search_id:
        q = q.filter(Business.search_id == search_id)
    businesses = q.all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(COLUMNS + ["score", "priority"])
    for b in businesses:
        row = [getattr(b, col) for col in COLUMNS]
        row.append(b.lead_score.total_score if b.lead_score else "")
        row.append(b.lead_score.priority if b.lead_score else "")
        writer.writerow(row)

    db.add(AuditLog(user_id=current_user.id, action="export_csv", entity_type="business",
                     meta={"count": len(businesses)}))
    db.commit()

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
