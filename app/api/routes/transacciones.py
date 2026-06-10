from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models import Transaccion
from app.schemas.transacciones import (
    ProfitMensual,
    TransaccionCreate,
    TransaccionResponse,
    TransaccionUpdate,
)

router = APIRouter(prefix="/transacciones", tags=["transacciones"])

INGRESO = 1
GASTO = 2


def _transaccion_base_query(db: Session):
    return db.query(Transaccion).options(joinedload(Transaccion.alumno))


@router.post("/", response_model=TransaccionResponse, status_code=201)
def create_transaccion(payload: TransaccionCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    if payload.tipo_transaccion not in (INGRESO, GASTO):
        raise HTTPException(status_code=400, detail="tipo_transaccion debe ser 1 (ingreso) o 2 (gasto)")

    transaccion = Transaccion(**payload.model_dump())
    db.add(transaccion)
    db.commit()
    return _transaccion_base_query(db).filter(Transaccion.id == transaccion.id).first()


@router.get("/", response_model=list[TransaccionResponse])
def list_transacciones(
    tipo_transaccion: int = Query(None, description="1=ingreso, 2=gasto"),
    categoria: str = Query(None),
    alumno_id: int = Query(None),
    fecha_desde: date = Query(None),
    fecha_hasta: date = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    q = _transaccion_base_query(db)
    if tipo_transaccion:
        q = q.filter(Transaccion.tipo_transaccion == tipo_transaccion)
    if categoria:
        q = q.filter(Transaccion.categoria == categoria)
    if alumno_id:
        q = q.filter(Transaccion.alumno_id == alumno_id)
    if fecha_desde:
        q = q.filter(Transaccion.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Transaccion.fecha <= fecha_hasta)
    return q.order_by(Transaccion.fecha.desc(), Transaccion.id.desc()).all()


@router.get("/{transaccion_id}", response_model=TransaccionResponse)
def get_transaccion(transaccion_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    t = _transaccion_base_query(db).filter(Transaccion.id == transaccion_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaccion no encontrada")
    return t


@router.put("/{transaccion_id}", response_model=TransaccionResponse)
def update_transaccion(transaccion_id: int, payload: TransaccionUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    t = db.query(Transaccion).filter(Transaccion.id == transaccion_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaccion no encontrada")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(t, field, value)

    db.commit()
    db.refresh(t)
    return _transaccion_base_query(db).filter(Transaccion.id == t.id).first()


@router.delete("/{transaccion_id}", status_code=204)
def delete_transaccion(transaccion_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    t = db.query(Transaccion).filter(Transaccion.id == transaccion_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transaccion no encontrada")

    db.delete(t)
    db.commit()


@router.get("/reportes/profit", response_model=list[ProfitMensual])
def profit_mensual(
    anio: int = Query(..., description="Año a consultar, ej. 2026"),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    rows = (
        db.query(
            func.to_char(Transaccion.fecha, "YYYY-MM").label("mes"),
            func.sum(case((Transaccion.tipo_transaccion == INGRESO, Transaccion.monto), else_=0)).label("ingresos"),
            func.sum(case((Transaccion.tipo_transaccion == GASTO, Transaccion.monto), else_=0)).label("gastos"),
        )
        .filter(func.extract("year", Transaccion.fecha) == anio)
        .group_by("mes")
        .order_by("mes")
        .all()
    )

    return [
        ProfitMensual(
            mes=row.mes,
            ingresos=round(row.ingresos, 2),
            gastos=round(row.gastos, 2),
            profit=round(row.ingresos - row.gastos, 2),
        )
        for row in rows
    ]
