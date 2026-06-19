from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models import AuditLog, User
from app.schemas.audit_logs import AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("/", response_model=list[AuditLogResponse])
def list_audit_logs(
    user_id: int = Query(None),
    action: str = Query(None),
    entity: str = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    q = db.query(AuditLog).options(joinedload(AuditLog.user))

    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if entity:
        q = q.filter(AuditLog.entity == entity)

    logs = q.order_by(desc(AuditLog.id)).limit(limit).all()

    result = []
    for log in logs:
        r = AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            entity=log.entity,
            entity_id=log.entity_id,
            descripcion=log.descripcion,
            created_at=log.created_at,
            user_nombre=log.user.full_name if log.user else None,
        )
        result.append(r)
    return result
