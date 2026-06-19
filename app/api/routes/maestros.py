import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_maestro, get_current_user, require_admin
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.security import hash_password
from app.models import Maestro, User
from app.schemas.maestros import (
    MaestroCreate,
    MaestroResponse,
    MaestroUpdate,
)

router = APIRouter(prefix="/maestros", tags=["maestros"])


def _maestro_base_query(db: Session):
    return db.query(Maestro).options(joinedload(Maestro.user))


def _generar_username(nombre: str, apellido_paterno: str) -> str:
    return nombre[0].upper() + apellido_paterno[0].upper() + apellido_paterno[1:].lower()


def _crear_usuario_maestro(nombre: str, apellido_paterno: str, db: Session) -> User:
    base_username = _generar_username(nombre, apellido_paterno)
    username = base_username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1

    password = secrets.token_urlsafe(8)

    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=f"{nombre} {apellido_paterno}",
        role_id=2,
    )
    db.add(user)
    db.flush()
    return user


@router.post("/", response_model=MaestroResponse, status_code=201)
def create_maestro(payload: MaestroCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    user_id = payload.user_id

    if user_id is not None:
        existing = db.query(Maestro).filter(Maestro.user_id == user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un maestro con ese user_id")
        user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
        if not user:
            raise HTTPException(status_code=400, detail="El usuario no existe")
    elif payload.fecha_nacimiento is not None:
        user = _crear_usuario_maestro(
            payload.nombre, payload.apellido_paterno, db
        )
        user_id = user.id

    data = payload.model_dump()
    data["user_id"] = user_id
    maestro = Maestro(**data)
    db.add(maestro)
    db.commit()

    audit_log(db, _admin.id, "CREATE", "maestro", maestro.id,
              f"{_admin.username} creó al maestro {maestro.nombre} {maestro.apellido_paterno}")

    return _maestro_base_query(db).filter(Maestro.id == maestro.id).first()


@router.get("/", response_model=list[MaestroResponse])
def list_maestros(
    include_deleted: bool = Query(False),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    q = _maestro_base_query(db)
    if current_maestro:
        q = q.filter(Maestro.id == current_maestro.id)
    else:
        if not include_deleted:
            q = q.filter(Maestro.is_deleted == False)
        if not include_inactive:
            q = q.filter(Maestro.is_active == True)
    return q.order_by(Maestro.id).all()


@router.get("/{maestro_id}", response_model=MaestroResponse)
def get_maestro(
    maestro_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    if current_maestro and maestro_id != current_maestro.id:
        raise HTTPException(status_code=403, detail="No autorizado")
    maestro = _maestro_base_query(db).filter(Maestro.id == maestro_id).first()
    if not maestro:
        raise HTTPException(status_code=404, detail="Maestro no encontrado")
    return maestro


@router.put("/{maestro_id}", response_model=MaestroResponse)
def update_maestro(maestro_id: int, payload: MaestroUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
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

    audit_log(db, _admin.id, "UPDATE", "maestro", maestro.id,
              f"{_admin.username} actualizó al maestro {maestro.nombre} {maestro.apellido_paterno}")

    return maestro


@router.delete("/{maestro_id}", status_code=204)
def delete_maestro(maestro_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    maestro = db.query(Maestro).filter(Maestro.id == maestro_id).first()
    if not maestro:
        raise HTTPException(status_code=404, detail="Maestro no encontrado")

    maestro.is_deleted = True
    maestro.is_active = False
    db.commit()

    audit_log(db, _admin.id, "DELETE", "maestro", maestro.id,
              f"{_admin.username} eliminó al maestro {maestro.nombre} {maestro.apellido_paterno}")
