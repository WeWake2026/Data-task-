import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from backend.app.models import AuditLog

def log_audit_event(
    db: Session,
    user_id: str,
    user_email: str,
    user_role: str,
    action: str,
    resource: str,
    outcome: str,
    ip_address: str = "127.0.0.1",
    request_id: str = None
):
    if not request_id:
        request_id = f"req-{uuid.uuid4().hex[:8]}"
    
    audit_entry = AuditLog(
        id=f"AUD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now(timezone.utc),
        user_id=user_id,
        user_email=user_email,
        user_role=user_role,
        action=action,
        resource=resource,
        outcome=outcome,
        request_id=request_id,
        ip_address=ip_address
    )
    db.add(audit_entry)
    db.commit()
    return audit_entry
