import logging

from sqlalchemy.orm import Session

from app.models.audit_logs import AuditLog

logger = logging.getLogger(__name__)


def audit_log(
    db: Session,
    user_id: int,
    action: str,
    entity: str,
    entity_id: int | None,
    descripcion: str,
) -> None:
    try:
        with db.begin_nested():
            db.add(AuditLog(
                user_id=user_id,
                action=action,
                entity=entity,
                entity_id=entity_id,
                descripcion=descripcion,
            ))
    except Exception as exc:
        logger.error("Error al registrar auditoria: %s", exc)
