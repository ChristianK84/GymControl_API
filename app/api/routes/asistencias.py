from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import require_maestro
from app.core.database import get_db
from app.models import Alumno, Asistencia, Membresia, TipoMembresia
from app.schemas.asistencias import (
    AsistenciaCreate,
    AsistenciaResponse,
    AsistenciaUpdate,
)

router = APIRouter(prefix="/asistencias", tags=["asistencias"])

ACTIVA = 1
PENDIENTE = 4

_DIA_MAP = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6,
}


def _parsear_dias(dias_incluidos: str) -> set[int]:
    normalizado = dias_incluidos.strip().lower()
    if normalizado == "libre":
        return set(range(7))
    partes = normalizado.split("-")
    if len(partes) == 2 and partes[0] in _DIA_MAP and partes[1] in _DIA_MAP:
        inicio, fin = _DIA_MAP[partes[0]], _DIA_MAP[partes[1]]
        if inicio <= fin:
            return set(range(inicio, fin + 1))
        return set(range(inicio, 7)) | set(range(0, fin + 1))
    dias = {_DIA_MAP.get(d.strip()) for d in normalizado.split(",")}
    dias.discard(None)
    return dias


def _validar_dia_permitido(fecha: date, dias_incluidos: str) -> bool:
    dias_permitidos = _parsear_dias(dias_incluidos)
    return fecha.weekday() in dias_permitidos


def _asistencia_base_query(db: Session):
    return db.query(Asistencia).options(
        joinedload(Asistencia.alumno),
        joinedload(Asistencia.maestro),
    )


def _membresia_activa(alumno_id: int, db: Session) -> Optional[Membresia]:
    return (
        db.query(Membresia)
        .options(joinedload(Membresia.tipo_membresia))
        .filter(
            Membresia.alumno_id == alumno_id,
            Membresia.estado_id.in_([ACTIVA, PENDIENTE]),
        )
        .order_by(Membresia.estado_id)
        .first()
    )


def _validar_visita_extra(alumno_id: int, fecha: date, db: Session) -> Optional[Decimal]:
    membresia = _membresia_activa(alumno_id, db)
    if not membresia or not membresia.tipo_membresia:
        raise HTTPException(status_code=400, detail="El alumno no tiene una membresia activa")

    tipo = membresia.tipo_membresia
    if _validar_dia_permitido(fecha, tipo.dias_incluidos):
        return None

    if not tipo.permite_dias_extra or tipo.costo_dia_extra is None:
        raise HTTPException(
            status_code=403,
            detail=f"Este dia no esta incluido en la membresia '{tipo.nombre}' ({tipo.dias_incluidos})",
        )

    return tipo.costo_dia_extra


def _validar_bloqueo_impago(alumno_id: int, db: Session) -> None:
    membresia = _membresia_activa(alumno_id, db)
    if not membresia or not membresia.tipo_membresia:
        return

    if membresia.pagado:
        return

    if membresia.tipo_membresia.bloquear_impago:
        raise HTTPException(
            status_code=402,
            detail=f"Membresia '{membresia.tipo_membresia.nombre}' pendiente de pago. Asistencia bloqueada.",
        )


def _enriquecer_impago(asistencia, db: Session):
    membresia = _membresia_activa(asistencia.alumno_id, db)
    if membresia and not membresia.pagado and membresia.tipo_membresia:
        asistencia.alerta_impago = (
            f"Atencion: membresia '{membresia.tipo_membresia.nombre}' pendiente de pago (${membresia.costo_real})"
        )
    else:
        asistencia.alerta_impago = None
    return asistencia


@router.post("/", response_model=AsistenciaResponse, status_code=201)
def create_asistencia(payload: AsistenciaCreate, db: Session = Depends(get_db), _maestro=Depends(require_maestro)):
    alumno = db.query(Alumno).filter(
        Alumno.id == payload.alumno_id, Alumno.is_deleted == False
    ).first()
    if not alumno:
        raise HTTPException(status_code=400, detail="Alumno no encontrado o inactivo")

    existing = db.query(Asistencia).filter(
        Asistencia.alumno_id == payload.alumno_id,
        Asistencia.fecha == payload.fecha,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe registro para este alumno en esta fecha")

    fecha_date = payload.fecha.date() if isinstance(payload.fecha, datetime) else payload.fecha

    _validar_bloqueo_impago(payload.alumno_id, db)

    costo_extra = _validar_visita_extra(payload.alumno_id, fecha_date, db)

    es_dia_extra = costo_extra is not None
    costo_final = costo_extra or Decimal("0")

    asistencia = Asistencia(**payload.model_dump())
    asistencia.es_dia_extra = es_dia_extra
    asistencia.costo_extra = costo_final
    db.add(asistencia)
    db.commit()
    return _enriquecer_impago(
        _asistencia_base_query(db).filter(Asistencia.id == asistencia.id).first(), db
    )


@router.get("/", response_model=list[AsistenciaResponse])
def list_asistencias(
    alumno_id: int = Query(None),
    maestro_id: int = Query(None),
    fecha_desde: datetime = Query(None),
    fecha_hasta: datetime = Query(None),
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
):
    q = _asistencia_base_query(db)
    if alumno_id:
        q = q.filter(Asistencia.alumno_id == alumno_id)
    if maestro_id:
        q = q.filter(Asistencia.maestro_id == maestro_id)
    if fecha_desde:
        q = q.filter(Asistencia.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Asistencia.fecha <= fecha_hasta)
    results = q.order_by(Asistencia.fecha.desc(), Asistencia.id).all()
    for a in results:
        _enriquecer_impago(a, db)
    return results


@router.get("/{asistencia_id}", response_model=AsistenciaResponse)
def get_asistencia(asistencia_id: int, db: Session = Depends(get_db), _maestro=Depends(require_maestro)):
    asistencia = _asistencia_base_query(db).filter(Asistencia.id == asistencia_id).first()
    if not asistencia:
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")
    return _enriquecer_impago(asistencia, db)


@router.put("/{asistencia_id}", response_model=AsistenciaResponse)
def update_asistencia(asistencia_id: int, payload: AsistenciaUpdate, db: Session = Depends(get_db), _maestro=Depends(require_maestro)):
    asistencia = _asistencia_base_query(db).filter(Asistencia.id == asistencia_id).first()
    if not asistencia:
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asistencia, field, value)

    db.commit()
    db.refresh(asistencia)
    return _enriquecer_impago(asistencia, db)


@router.delete("/{asistencia_id}", status_code=204)
def delete_asistencia(asistencia_id: int, db: Session = Depends(get_db), _maestro=Depends(require_maestro)):
    asistencia = db.query(Asistencia).filter(Asistencia.id == asistencia_id).first()
    if not asistencia:
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")

    db.delete(asistencia)
    db.commit()
