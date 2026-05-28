from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import require_maestro
from app.core.database import get_db
from app.models import Alumno, Asistencia, Membresia
from app.schemas.asistencias import (
    AsistenciaCreate,
    AsistenciaResponse,
    AsistenciaUpdate,
)

router = APIRouter(prefix="/asistencias", tags=["asistencias"])


def _asistencia_base_query(db: Session):
    return db.query(Asistencia).options(
        joinedload(Asistencia.alumno),
        joinedload(Asistencia.maestro),
    )


def _enriquecer_impago(asistencia, db: Session):
    """Agrega alerta_impago si el alumno tiene membresia activa sin pagar."""
    membresia = (
        db.query(Membresia)
        .options(joinedload(Membresia.tipo_membresia))
        .filter(
            Membresia.alumno_id == asistencia.alumno_id,
            Membresia.estado_id.in_([1, 4]),
            Membresia.pagado == False,
        )
        .first()
    )
    if membresia and membresia.tipo_membresia:
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

    asistencia = Asistencia(**payload.model_dump())
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
