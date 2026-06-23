from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TransaccionCreate(BaseModel):
    tipo_transaccion: int = Field(ge=1, le=2, description="1=ingreso, 2=gasto")
    categoria: str = Field(max_length=100)
    subcategoria: Optional[str] = Field(default=None, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    monto: Decimal = Field(max_digits=10, decimal_places=2, ge=0)
    fecha: date
    membresia_id: Optional[int] = Field(default=None, gt=0)
    alumno_id: Optional[int] = Field(default=None, gt=0)
    registrado_por: Optional[int] = Field(default=None, gt=0)


class TransaccionUpdate(BaseModel):
    tipo_transaccion: Optional[int] = Field(default=None, ge=1, le=2)
    categoria: Optional[str] = Field(default=None, max_length=100)
    subcategoria: Optional[str] = Field(default=None, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    monto: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2, ge=0)
    fecha: Optional[date] = None
    membresia_id: Optional[int] = Field(default=None, gt=0)
    alumno_id: Optional[int] = Field(default=None, gt=0)


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
