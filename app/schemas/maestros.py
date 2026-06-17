from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class MaestroCreate(BaseModel):
    user_id: Optional[int] = Field(default=None, gt=0)
    nombre: str = Field(max_length=100)
    apellido_paterno: str = Field(max_length=100)
    apellido_materno: Optional[str] = Field(default=None, max_length=100)
    telefono: Optional[str] = Field(default=None, max_length=20)
    foto: Optional[str] = Field(default=None, max_length=500)
    fecha_nacimiento: Optional[date] = None


class MaestroUpdate(BaseModel):
    user_id: Optional[int] = Field(default=None, gt=0)
    nombre: Optional[str] = Field(default=None, max_length=100)
    apellido_paterno: Optional[str] = Field(default=None, max_length=100)
    apellido_materno: Optional[str] = Field(default=None, max_length=100)
    telefono: Optional[str] = Field(default=None, max_length=20)
    foto: Optional[str] = Field(default=None, max_length=500)
    fecha_nacimiento: Optional[date] = None
    is_active: Optional[bool] = None


class MaestroUserInfo(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role_id: int

    model_config = {"from_attributes": True}


class MaestroResponse(BaseModel):
    id: int
    user_id: Optional[int]
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str]
    telefono: Optional[str]
    foto: Optional[str]
    fecha_nacimiento: Optional[date]
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    user: Optional[MaestroUserInfo] = None

    model_config = {"from_attributes": True}
