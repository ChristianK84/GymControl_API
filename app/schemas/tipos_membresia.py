from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TipoMembresiaCreate(BaseModel):
    nombre: str = Field(max_length=100)
    descripcion: Optional[str] = None
    costo_base: Decimal
    duracion_dias: int
    dias_incluidos: str = Field(max_length=20)
    dias_por_semana: Optional[int] = None
    horas_por_clase: Optional[int] = None
    nivel_competitivo: bool = False
    color: Optional[str] = None
    permite_dias_extra: bool = False
    costo_dia_extra: Optional[Decimal] = None
    bloquear_impago: bool = False


class TipoMembresiaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    costo_base: Optional[Decimal] = None
    duracion_dias: Optional[int] = None
    dias_incluidos: Optional[str] = None
    dias_por_semana: Optional[int] = None
    horas_por_clase: Optional[int] = None
    nivel_competitivo: Optional[bool] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None
    permite_dias_extra: Optional[bool] = None
    costo_dia_extra: Optional[Decimal] = None
    bloquear_impago: Optional[bool] = None


class TipoMembresiaResponse(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    costo_base: Decimal
    duracion_dias: int
    dias_incluidos: str
    dias_por_semana: Optional[int]
    horas_por_clase: Optional[int]
    nivel_competitivo: bool
    color: Optional[str]
    permite_dias_extra: bool
    costo_dia_extra: Optional[Decimal]
    bloquear_impago: bool
    is_active: bool
    is_deleted: bool
    created_at: datetime

    model_config = {"from_attributes": True}
