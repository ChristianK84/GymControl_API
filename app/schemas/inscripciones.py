from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class InscripcionAlumnoInfo(BaseModel):
    id: int
    nombrecompleto: str
    apellido_paterno: str
    apellido_materno: Optional[str]
    rama: str
    fotografia: Optional[str] = None

    model_config = {"from_attributes": True}


class InscripcionCreate(BaseModel):
    alumno_id: int = Field(gt=0)
    monto: Decimal = Field(max_digits=10, decimal_places=2, ge=0)
    porcentaje_beca: int = Field(default=0, ge=0, le=100)
    anio: int = Field(ge=2000, le=2100)
    fecha_pago: date
    fecha_inicio: date
    fecha_fin: date
    pagado: bool = True
    notas: Optional[str] = Field(default=None, max_length=500)


class InscripcionUpdate(BaseModel):
    monto: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2, ge=0)
    porcentaje_beca: Optional[int] = Field(default=None, ge=0, le=100)
    anio: Optional[int] = Field(default=None, ge=2000, le=2100)
    fecha_pago: Optional[date] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    pagado: Optional[bool] = None
    notas: Optional[str] = Field(default=None, max_length=500)


class InscripcionResponse(BaseModel):
    id: int
    alumno_id: int
    monto: Decimal
    porcentaje_beca: int
    monto_final: Decimal
    anio: int
    fecha_pago: date
    fecha_inicio: date
    fecha_fin: date
    pagado: bool
    notas: Optional[str]
    registrado_por: Optional[int]
    created_at: datetime
    alumno: Optional[InscripcionAlumnoInfo] = None

    model_config = {"from_attributes": True}
