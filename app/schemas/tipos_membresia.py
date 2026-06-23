from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TipoMembresiaCreate(BaseModel):
    nombre: str = Field(max_length=100)
    descripcion: Optional[str] = None
    costo_base: Decimal = Field(max_digits=10, decimal_places=2)
    duracion_dias: int
    dias_incluidos: str = Field(max_length=20)
    dias_por_semana: Optional[int] = None
    horas_por_clase: Optional[int] = None
    nivel_competitivo: bool = False
    color: Optional[str] = None
    permite_dias_extra: bool = False
    costo_dia_extra: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    bloquear_impago: bool = False

    @field_validator("dias_incluidos")
    @classmethod
    def validar_dias(cls, v: str) -> str:
        from app.api.routes.asistencias import _parsear_dias
        if not _parsear_dias(v):
            raise ValueError(f"'{v}' no contiene días válidos. Use nombres completos (ej. lunes-viernes)")
        return v


class TipoMembresiaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    costo_base: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    duracion_dias: Optional[int] = None
    dias_incluidos: Optional[str] = None
    dias_por_semana: Optional[int] = None
    horas_por_clase: Optional[int] = None
    nivel_competitivo: Optional[bool] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None
    permite_dias_extra: Optional[bool] = None
    costo_dia_extra: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    bloquear_impago: Optional[bool] = None

    @field_validator("dias_incluidos")
    @classmethod
    def validar_dias(cls, v: str) -> str:
        if v is None:
            return v
        from app.api.routes.asistencias import _parsear_dias
        if not _parsear_dias(v):
            raise ValueError(f"'{v}' no contiene días válidos")
        return v


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
