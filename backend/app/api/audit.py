from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import AuditLog, User
from backend.app.schemas import AuditLogResponse
from backend.app.security.dependencies import require_admin

router = APIRouter(prefix="/audit-events", tags=["Audit Logs"])

@router.get("", response_model=List[AuditLogResponse])
def get_audit_events(
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin)
):
    query = db.query(AuditLog)
    if search:
        s = f"%{search}%"
        query = query.filter(
            (AuditLog.action.ilike(s)) |
            (AuditLog.resource.ilike(s)) |
            (AuditLog.user_email.ilike(s))
        )
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    return [
        AuditLogResponse(
            id=log.id,
            timestamp=log.timestamp,
            user=log.user_email,
            role=log.user_role,
            action=log.action,
            resource=log.resource,
            outcome=log.outcome,
            request_id=log.request_id,
            ip=log.ip_address
        )
        for log in logs
    ]
