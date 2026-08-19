from datetime import date

from pydantic import BaseModel


class SemanaAsistencias(BaseModel):
    semana_iso: str
    fecha_inicio: date
    fecha_fin: date
    total_asistencias: int


class MaestroAsistencias(BaseModel):
    maestro_id: int
    maestro_nombre: str
    maestro_apellido_paterno: str
    total_general: int
    semanas: dict[str, int]


class AsistenciasPorMaestroResponse(BaseModel):
    fecha_inicio_global: date
    fecha_fin_global: date
    semanas: list[str]
    maestros: list[MaestroAsistencias]
