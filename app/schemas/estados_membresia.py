from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EstadoMembresiaResponse(BaseModel):
    id: int
    nombre: str
    color: Optional[str]
    descripcion: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
