from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AsistenciaCreate(BaseModel):
    alumno_id: int
    maestro_id: int
    fecha: datetime
    asistio: bool
    notas: Optional[str] = None
    registrado_por: Optional[int] = None


class AsistenciaUpdate(BaseModel):
    asistio: Optional[bool] = None
    notas: Optional[str] = None
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
    created_at: datetime
    alumno: Optional[AsistenciaAlumnoInfo] = None
    maestro: Optional[AsistenciaMaestroInfo] = None

    model_config = {"from_attributes": True}
