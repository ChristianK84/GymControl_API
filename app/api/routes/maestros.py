from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Maestro, User
from app.schemas.maestros import (
    MaestroCreate,
    MaestroResponse,
    MaestroUpdate,
)

router = APIRouter(prefix="/maestros", tags=["maestros"])


def _maestro_base_query(db: Session):
    return db.query(Maestro).options(joinedload(Maestro.user))


@router.post("/", response_model=MaestroResponse, status_code=201)
def create_maestro(payload: MaestroCreate, db: Session = Depends(get_db)):
    if payload.user_id is not None:
        existing = db.query(Maestro).filter(Maestro.user_id == payload.user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un maestro con ese user_id")
        user = db.query(User).filter(User.id == payload.user_id, User.is_deleted == False).first()
        if not user:
            raise HTTPException(status_code=400, detail="El usuario no existe")

    maestro = Maestro(**payload.model_dump())
    db.add(maestro)
    db.commit()
    return _maestro_base_query(db).filter(Maestro.id == maestro.id).first()


@router.get("/", response_model=list[MaestroResponse])
def list_maestros(
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = _maestro_base_query(db)
    if not include_deleted:
        q = q.filter(Maestro.is_deleted == False)
    return q.order_by(Maestro.id).all()


@router.get("/{maestro_id}", response_model=MaestroResponse)
def get_maestro(maestro_id: int, db: Session = Depends(get_db)):
    maestro = _maestro_base_query(db).filter(Maestro.id == maestro_id).first()
    if not maestro:
        raise HTTPException(status_code=404, detail="Maestro no encontrado")
    return maestro


@router.put("/{maestro_id}", response_model=MaestroResponse)
def update_maestro(maestro_id: int, payload: MaestroUpdate, db: Session = Depends(get_db)):
    maestro = _maestro_base_query(db).filter(Maestro.id == maestro_id).first()
    if not maestro:
        raise HTTPException(status_code=404, detail="Maestro no encontrado")

    if payload.user_id is not None and payload.user_id != maestro.user_id:
        existing = db.query(Maestro).filter(Maestro.user_id == payload.user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un maestro con ese user_id")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(maestro, field, value)

    db.commit()
    db.refresh(maestro)
    return maestro


@router.delete("/{maestro_id}", status_code=204)
def delete_maestro(maestro_id: int, db: Session = Depends(get_db)):
    maestro = db.query(Maestro).filter(Maestro.id == maestro_id).first()
    if not maestro:
        raise HTTPException(status_code=404, detail="Maestro no encontrado")

    maestro.is_deleted = True
    maestro.is_active = False
    db.commit()
