from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ── Membresia ──

class MembresiaCreate(BaseModel):
    alumno_id: int
    tipo_membresia_id: int
    costo_real: Decimal
    porcentaje_beca: int = 0
    fecha_inicio: date
    fecha_vencimiento: date
    pagado: bool = True
    notas: Optional[str] = None


class MembresiaUpdate(BaseModel):
    tipo_membresia_id: Optional[int] = None
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
