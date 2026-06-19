from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ── Membresia ──

class MembresiaCreate(BaseModel):
    alumno_id: int = Field(gt=0)
    tipo_membresia_id: int = Field(gt=0)
    costo_real: Decimal = Field(max_digits=10, decimal_places=2, ge=0)
    porcentaje_beca: int = Field(default=0, ge=0, le=100)
    fecha_inicio: date
    fecha_vencimiento: date
    pagado: bool = True
    notas: Optional[str] = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validar_fechas(self) -> "MembresiaCreate":
        if self.fecha_vencimiento <= self.fecha_inicio:
            raise ValueError("fecha_vencimiento debe ser posterior a fecha_inicio")
        return self


class MembresiaUpdate(BaseModel):
    tipo_membresia_id: Optional[int] = Field(default=None, gt=0)
    costo_real: Optional[Decimal] = None
    porcentaje_beca: Optional[int] = None
    fecha_inicio: Optional[date] = None
    fecha_vencimiento: Optional[date] = None
    estado_id: Optional[int] = None
    pagado: Optional[bool] = None
    notas: Optional[str] = None


# ── Nested info para response ──

class MembresiaAlumnoInfo(BaseModel):
    id: int
    nombrecompleto: str
    apellido_paterno: str
    apellido_materno: Optional[str]
    rama: str
    fotografia: Optional[str] = None

    model_config = {"from_attributes": True}


class MembresiaTipoInfo(BaseModel):
    id: int
    nombre: str
    costo_base: Decimal
    duracion_dias: int
    dias_incluidos: str
    color: Optional[str]

    model_config = {"from_attributes": True}


class MembresiaEstadoInfo(BaseModel):
    id: int
    nombre: str
    color: Optional[str]

    model_config = {"from_attributes": True}


class MembresiaResponse(BaseModel):
    id: int
    alumno_id: int
    tipo_membresia_id: int
    costo_real: Decimal
    porcentaje_beca: int
    fecha_inicio: date
    fecha_vencimiento: date
    estado_id: int
    pagado: bool
    notas: Optional[str]
    created_at: datetime
    updated_at: datetime
    alumno: Optional[MembresiaAlumnoInfo] = None
    tipo_membresia: Optional[MembresiaTipoInfo] = None
    estado: Optional[MembresiaEstadoInfo] = None

    model_config = {"from_attributes": True}
