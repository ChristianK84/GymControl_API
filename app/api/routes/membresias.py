from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_maestro, require_maestro
from app.core.database import get_db
from app.models import Alumno, Maestro, Membresia, TipoMembresia
from app.schemas.membresias import (
    MembresiaCreate,
    MembresiaResponse,
    MembresiaUpdate,
)

router = APIRouter(prefix="/membresias", tags=["membresias"])

# IDs de estados
ACTIVA = 1
VENCIDA = 2
CANCELADA = 3


def _membresia_base_query(db: Session):
    return db.query(Membresia).options(
        joinedload(Membresia.alumno),
        joinedload(Membresia.tipo_membresia),
        joinedload(Membresia.estado),
    )


def _actualizar_estados_vencidos(db: Session):
    """Actualiza a Vencida las membresias cuya fecha ya paso y aun estan Activa."""
    hoy = date.today()
    vencidas = db.query(Membresia).filter(
        Membresia.fecha_vencimiento < hoy,
        Membresia.estado_id == ACTIVA,
    ).all()
    for m in vencidas:
        m.estado_id = VENCIDA
    if vencidas:
        db.commit()


@router.post("/", response_model=MembresiaResponse, status_code=201)
def create_membresia(
    payload: MembresiaCreate,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    alumno = db.query(Alumno).filter(
        Alumno.id == payload.alumno_id, Alumno.is_deleted == False
    ).first()
    if not alumno:
        raise HTTPException(status_code=400, detail="Alumno no encontrado o inactivo")
    if current_maestro and alumno.maestro_id != current_maestro.id:
        raise HTTPException(status_code=403, detail="No autorizado para este alumno")

    tipo = db.query(TipoMembresia).filter(
        TipoMembresia.id == payload.tipo_membresia_id, TipoMembresia.is_deleted == False
    ).first()
    if not tipo:
        raise HTTPException(status_code=400, detail="Tipo de membresia no encontrado")

    membresia = Membresia(
        alumno_id=payload.alumno_id,
        tipo_membresia_id=payload.tipo_membresia_id,
        costo_real=payload.costo_real,
        porcentaje_beca=payload.porcentaje_beca,
        fecha_inicio=payload.fecha_inicio,
        fecha_vencimiento=payload.fecha_vencimiento,
        estado_id=ACTIVA,
        pagado=payload.pagado,
        notas=payload.notas,
    )
    db.add(membresia)
    db.commit()
    return _membresia_base_query(db).filter(Membresia.id == membresia.id).first()


@router.get("/", response_model=list[MembresiaResponse])
def list_membresias(
    alumno_id: int = Query(None),
    estado_id: int = Query(None),
    pagado: bool = Query(None),
    vencidas: bool = Query(False),
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    _actualizar_estados_vencidos(db)

    q = _membresia_base_query(db)
    if current_maestro:
        q = q.join(Alumno, Membresia.alumno_id == Alumno.id).filter(Alumno.maestro_id == current_maestro.id)
    if alumno_id:
        q = q.filter(Membresia.alumno_id == alumno_id)
    if estado_id:
        q = q.filter(Membresia.estado_id == estado_id)
    if vencidas:
        q = q.filter(Membresia.estado_id == VENCIDA)
    if pagado is not None:
        q = q.filter(Membresia.pagado == pagado)
    return q.order_by(Membresia.fecha_vencimiento.desc()).all()


@router.get("/impagas", response_model=list[MembresiaResponse])
def list_membresias_impagas(
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    _actualizar_estados_vencidos(db)

    q = (
        _membresia_base_query(db)
        .filter(
            Membresia.estado_id == ACTIVA,
            Membresia.pagado == False,
        )
    )
    if current_maestro:
        q = q.join(Alumno, Membresia.alumno_id == Alumno.id).filter(Alumno.maestro_id == current_maestro.id)
    return q.order_by(Membresia.fecha_vencimiento.asc()).all()


def _autorizar_membresia(membresia_id: int, db: Session, current_maestro: Maestro | None):
    """Obtiene una membresia y verifica que el maestro tenga acceso al alumno."""
    membresia = _membresia_base_query(db).filter(Membresia.id == membresia_id).first()
    if not membresia:
        raise HTTPException(status_code=404, detail="Membresia no encontrada")
    if current_maestro:
        alumno = db.query(Alumno).filter(Alumno.id == membresia.alumno_id).first()
        if not alumno or alumno.maestro_id != current_maestro.id:
            raise HTTPException(status_code=403, detail="No autorizado para esta membresia")
    return membresia


@router.get("/{membresia_id}", response_model=MembresiaResponse)
def get_membresia(
    membresia_id: int,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    _actualizar_estados_vencidos(db)
    return _autorizar_membresia(membresia_id, db, current_maestro)


@router.put("/{membresia_id}", response_model=MembresiaResponse)
def update_membresia(
    membresia_id: int,
    payload: MembresiaUpdate,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    membresia = _autorizar_membresia(membresia_id, db, current_maestro)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(membresia, field, value)

    db.commit()
    db.refresh(membresia)
    return membresia


@router.delete("/{membresia_id}", status_code=204)
def cancelar_membresia(
    membresia_id: int,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    membresia = _autorizar_membresia(membresia_id, db, current_maestro)

    membresia.estado_id = CANCELADA
    db.commit()
