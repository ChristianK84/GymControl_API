from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models import Rol
from app.schemas.roles import RolResponse

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/", response_model=list[RolResponse])
def list_roles(db: Session = Depends(get_db), _user=Depends(get_current_user)):
    return db.query(Rol).order_by(Rol.id).all()


@router.get("/{rol_id}", response_model=RolResponse)
def get_rol(rol_id: int, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return rol
