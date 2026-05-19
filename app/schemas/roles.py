from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RolResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
