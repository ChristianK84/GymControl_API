from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TransaccionCreate(BaseModel):
    tipo_transaccion: int = Field(description="1=ingreso, 2=gasto")
    categoria: str = Field(max_length=100)
    subcategoria: Optional[str] = None
    descripcion: Optional[str] = None
    monto: Decimal
    fecha: date
    membresia_id: Optional[int] = None
    alumno_id: Optional[int] = None
    registrado_por: Optional[int] = None


class TransaccionUpdate(BaseModel):
    tipo_transaccion: Optional[int] = None
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    descripcion: Optional[str] = None
    monto: Optional[Decimal] = None
    fecha: Optional[date] = None
    membresia_id: Optional[int] = None
    alumno_id: Optional[int] = None


class TransaccionAlumnoInfo(BaseModel):
    id: int
    nombrecompleto: str
    apellido_paterno: str

    model_config = {"from_attributes": True}


class TransaccionResponse(BaseModel):
    id: int
    tipo_transaccion: int
    categoria: str
    subcategoria: Optional[str]
    descripcion: Optional[str]
    monto: Decimal
    fecha: date
    membresia_id: Optional[int]
    alumno_id: Optional[int]
    registrado_por: Optional[int]
    created_at: datetime
    alumno: Optional[TransaccionAlumnoInfo] = None

    model_config = {"from_attributes": True}


class ProfitMensual(BaseModel):
    mes: str
    ingresos: Decimal
    gastos: Decimal
    profit: Decimal
