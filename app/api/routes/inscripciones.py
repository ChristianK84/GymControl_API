import logging
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import require_maestro
from app.core.audit import audit_log
from app.core.database import get_db
from app.models import Alumno, Inscripcion
from app.schemas.inscripciones import (
    InscripcionCreate,
    InscripcionResponse,
    InscripcionUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inscripciones", tags=["inscripciones"])


def _base_query(db: Session):
    return db.query(Inscripcion).options(
        joinedload(Inscripcion.alumno),
    ).filter(Inscripcion.is_deleted == False)


@router.post("/", response_model=InscripcionResponse, status_code=201)
def create_inscripcion(
    payload: InscripcionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_maestro),
):
    alumno = db.query(Alumno).filter(
        Alumno.id == payload.alumno_id, Alumno.is_deleted == False
    ).first()
    if not alumno:
        raise HTTPException(status_code=400, detail="Alumno no encontrado")

    vigente = _base_query(db).filter(
        Inscripcion.alumno_id == payload.alumno_id,
        Inscripcion.fecha_fin >= date.today(),
    ).first()
    if vigente:
        raise HTTPException(
            status_code=400,
            detail=f"El alumno ya tiene una inscripcion vigente hasta {vigente.fecha_fin}",
        )

    beca = payload.porcentaje_beca
    monto_final = payload.monto * (1 - Decimal(beca) / Decimal(100))

    inscripcion = Inscripcion(
        alumno_id=payload.alumno_id,
        monto=payload.monto,
        porcentaje_beca=beca,
        monto_final=monto_final,
        anio=payload.anio,
        fecha_pago=payload.fecha_pago,
        fecha_inicio=payload.fecha_inicio,
        fecha_fin=payload.fecha_fin,
        pagado=payload.pagado,
        notas=payload.notas,
        registrado_por=current_user.id,
    )
    db.add(inscripcion)
    db.commit()

    audit_log(db, current_user.id, "CREATE", "inscripcion", inscripcion.id,
              f"{current_user.username} creo inscripcion para alumno {alumno.nombrecompleto} {alumno.apellido_paterno}")

    return _base_query(db).filter(Inscripcion.id == inscripcion.id).first()


@router.get("/", response_model=list[InscripcionResponse])
def list_inscripciones(
    alumno_id: int = Query(None),
    anio: int = Query(None),
    pagado: bool = Query(None),
    limit: int = Query(None, ge=1, le=1000),
    offset: int = Query(None, ge=0),
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
):
    q = _base_query(db)
    if alumno_id:
        q = q.filter(Inscripcion.alumno_id == alumno_id)
    if anio:
        q = q.filter(Inscripcion.anio == anio)
    if pagado is not None:
        q = q.filter(Inscripcion.pagado == pagado)
    results = q.order_by(Inscripcion.anio.desc(), Inscripcion.created_at.desc())
    if limit:
        results = results.limit(limit)
    if offset:
        results = results.offset(offset)
    return results.all()


@router.get("/{inscripcion_id}", response_model=InscripcionResponse)
def get_inscripcion(
    inscripcion_id: int,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
):
    inscripcion = _base_query(db).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripcion no encontrada")
    return inscripcion


@router.put("/{inscripcion_id}", response_model=InscripcionResponse)
def update_inscripcion(
    inscripcion_id: int,
    payload: InscripcionUpdate,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
):
    inscripcion = _base_query(db).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripcion no encontrada")

    update_data = payload.model_dump(exclude_unset=True)
    if "porcentaje_beca" in update_data or "monto" in update_data:
        monto = update_data.get("monto", inscripcion.monto)
        beca = update_data.get("porcentaje_beca", inscripcion.porcentaje_beca)
        update_data["monto_final"] = monto * (1 - Decimal(beca) / Decimal(100))

    for field, value in update_data.items():
        setattr(inscripcion, field, value)

    db.commit()
    db.refresh(inscripcion)

    audit_log(db, _maestro.id, "UPDATE", "inscripcion", inscripcion.id,
              f"{_maestro.username} actualizo inscripcion ID {inscripcion.id}")

    return _base_query(db).filter(Inscripcion.id == inscripcion.id).first()


@router.delete("/{inscripcion_id}", status_code=204)
def delete_inscripcion(
    inscripcion_id: int,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
):
    inscripcion = _base_query(db).filter(Inscripcion.id == inscripcion_id).first()
    if not inscripcion:
        raise HTTPException(status_code=404, detail="Inscripcion no encontrada")

    inscripcion.is_deleted = True
    db.commit()

    audit_log(db, _maestro.id, "DELETE", "inscripcion", inscripcion_id,
              f"{_maestro.username} elimino inscripcion ID {inscripcion_id}")
