from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class AsistenciaCreate(BaseModel):
    alumno_id: int = Field(gt=0)
    maestro_id: int = Field(gt=0)
    fecha: datetime
    asistio: bool
    notas: Optional[str] = Field(default=None, max_length=500)
    registrado_por: Optional[int] = Field(default=None, gt=0)
    es_dia_extra: bool = False
    costo_extra: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)


class AsistenciaUpdate(BaseModel):
    asistio: Optional[bool] = None
    notas: Optional[str] = Field(default=None, max_length=500)
    maestro_id: Optional[int] = None


class AsistenciaAlumnoInfo(BaseModel):
    id: int
    nombrecompleto: str
    apellido_paterno: str
    apellido_materno: Optional[str]
    rama: str

    model_config = {"from_attributes": True}


class AsistenciaMaestroInfo(BaseModel):
    id: int
    nombre: str
    apellido_paterno: str

    model_config = {"from_attributes": True}


class AsistenciaResponse(BaseModel):
    id: int
    alumno_id: int
    maestro_id: int
    fecha: datetime
    asistio: bool
    notas: Optional[str]
    registrado_por: Optional[int]
    es_dia_extra: bool
    costo_extra: Decimal
    created_at: datetime
    alerta_impago: Optional[str] = None
    alumno: Optional[AsistenciaAlumnoInfo] = None
    maestro: Optional[AsistenciaMaestroInfo] = None

    model_config = {"from_attributes": True}


class AsistenciaScanRequest(BaseModel):
    alumno_id: int = Field(gt=0)
    maestro_id: int = Field(gt=0)


class AsistenciaScanResponse(BaseModel):
    permitido: bool
    motivo: str
    mensaje: str
    costo_extra: Optional[Decimal] = None
    asistencia: Optional[AsistenciaResponse] = None
