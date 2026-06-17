from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.models import TipoMembresia
from app.schemas.tipos_membresia import (
    TipoMembresiaCreate,
    TipoMembresiaResponse,
    TipoMembresiaUpdate,
)

router = APIRouter(prefix="/tipos-membresia", tags=["tipos-membresia"])


@router.post("/", response_model=TipoMembresiaResponse, status_code=201)
def create_tipo(payload: TipoMembresiaCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    tipo = TipoMembresia(**payload.model_dump())
    db.add(tipo)
    db.commit()
    db.refresh(tipo)
    return tipo


@router.get("/", response_model=list[TipoMembresiaResponse])
def list_tipos(
    include_deleted: bool = Query(False),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    _current=Depends(get_current_user),
):
    q = db.query(TipoMembresia)
    if not include_deleted:
        q = q.filter(TipoMembresia.is_deleted == False)
    if not include_inactive:
        q = q.filter(TipoMembresia.is_active == True)
    return q.order_by(TipoMembresia.id).all()


@router.get("/{tipo_id}", response_model=TipoMembresiaResponse)
def get_tipo(tipo_id: int, db: Session = Depends(get_db), _current=Depends(get_current_user)):
    tipo = db.query(TipoMembresia).filter(TipoMembresia.id == tipo_id, TipoMembresia.is_deleted == False).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de membresia no encontrado")
    return tipo


@router.put("/{tipo_id}", response_model=TipoMembresiaResponse)
def update_tipo(tipo_id: int, payload: TipoMembresiaUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    tipo = db.query(TipoMembresia).filter(TipoMembresia.id == tipo_id, TipoMembresia.is_deleted == False).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de membresia no encontrado")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tipo, field, value)

    db.commit()
    db.refresh(tipo)
    return tipo


@router.delete("/{tipo_id}", status_code=204)
def delete_tipo(tipo_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    tipo = db.query(TipoMembresia).filter(TipoMembresia.id == tipo_id, TipoMembresia.is_deleted == False).first()
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de membresia no encontrado")

    tipo.is_deleted = True
    tipo.is_active = False
    db.commit()
