from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    entity: str
    entity_id: int | None
    descripcion: str
    created_at: datetime
    user_nombre: str | None = None

    model_config = {"from_attributes": True}
