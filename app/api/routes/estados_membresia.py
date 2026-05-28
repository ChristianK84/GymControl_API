from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import EstadoMembresia
from app.schemas.estados_membresia import EstadoMembresiaResponse

router = APIRouter(prefix="/estados-membresia", tags=["estados-membresia"])


@router.get("/", response_model=list[EstadoMembresiaResponse])
def list_estados(db: Session = Depends(get_db)):
    return db.query(EstadoMembresia).order_by(EstadoMembresia.id).all()


@router.get("/{estado_id}", response_model=EstadoMembresiaResponse)
def get_estado(estado_id: int, db: Session = Depends(get_db)):
    estado = db.query(EstadoMembresia).filter(EstadoMembresia.id == estado_id).first()
    if not estado:
        raise HTTPException(status_code=404, detail="Estado de membresia no encontrado")
    return estado
