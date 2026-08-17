import secrets
from datetime import date

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

ALLOWED_SELF_FIELDS = {
    'nombre', 'apellido_paterno', 'apellido_materno',
    'telefono', 'email', 'fecha_nacimiento', 'foto',
}

router = APIRouter(prefix="/maestros", tags=["maestros"])


def _maestro_base_query(db: Session):
    return db.query(Maestro).options(joinedload(Maestro.user))


def _generar_username(nombre: str, apellido_paterno: str) -> str:
    return nombre[0].upper() + apellido_paterno[0].upper() + apellido_paterno[1:].lower()


def _crear_usuario_maestro(
    nombre: str,
    apellido_paterno: str,
    fecha_nacimiento: date,
    db: Session,
) -> tuple[User, str]:
    base_username = _generar_username(nombre, apellido_paterno)
    username = base_username
    counter = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1

    apellido = apellido_paterno.split()[0].lower()
    last_two = str(fecha_nacimiento.year)[-2:]
    password = f"{nombre[0].lower()}{apellido}{last_two}"

    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=f"{nombre} {apellido_paterno}",
        role_id=2,
    )
    db.add(user)
    db.flush()
    return user, password


@router.post("/", response_model=MaestroResponse, status_code=201)
def create_maestro(payload: MaestroCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    user_id = payload.user_id
    generated_password = None

    if user_id is not None:
        existing = db.query(Maestro).filter(Maestro.user_id == user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un maestro con ese user_id")
        user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
        if not user:
            raise HTTPException(status_code=400, detail="El usuario no existe")
    elif payload.fecha_nacimiento is not None:
        user, generated_password = _crear_usuario_maestro(
            payload.nombre, payload.apellido_paterno, payload.fecha_nacimiento, db
        )
        user_id = user.id
    else:
        raise HTTPException(status_code=400,
                            detail="Debe proporcionar user_id o fecha_nacimiento para crear un maestro")

    data = payload.model_dump()
    data["user_id"] = user_id
    maestro = Maestro(**data)
    db.add(maestro)
    db.commit()

    audit_log(db, _admin.id, "CREATE", "maestro", maestro.id,
              f"{_admin.username} creó al maestro {maestro.nombre} {maestro.apellido_paterno}")

    result = _maestro_base_query(db).filter(Maestro.id == maestro.id).first()
    response = MaestroResponse.model_validate(result)
    if generated_password:
        response.generated_password = generated_password
    return response


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
def update_maestro(
    maestro_id: int,
    payload: MaestroUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    maestro = _maestro_base_query(db).filter(Maestro.id == maestro_id).first()
    if not maestro:
        raise HTTPException(status_code=404, detail="Maestro no encontrado")

    is_admin = current_user.role_id == 1
    is_self = current_maestro is not None and current_maestro.id == maestro_id

    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="No autorizado")

    update_data = payload.model_dump(exclude_unset=True)

    # Maestro solo puede editar campos permitidos (no is_active ni user_id)
    if not is_admin:
        update_data = {k: v for k, v in update_data.items() if k in ALLOWED_SELF_FIELDS}

    # Validar reasignación de user_id (solo admin)
    if 'user_id' in update_data and update_data['user_id'] is not None:
        new_user_id = update_data['user_id']
        if new_user_id != maestro.user_id:
            existing = db.query(Maestro).filter(Maestro.user_id == new_user_id).first()
            if existing:
                raise HTTPException(status_code=400, detail="Ya existe un maestro con ese user_id")
            user = db.query(User).filter(User.id == new_user_id, User.is_deleted == False).first()
            if not user:
                raise HTTPException(status_code=400, detail="El usuario no existe")

    for field, value in update_data.items():
        setattr(maestro, field, value)

    db.commit()
    db.refresh(maestro)

    audit_log(db, current_user.id, "UPDATE", "maestro", maestro.id,
              f"{current_user.username} actualizó al maestro {maestro.nombre} {maestro.apellido_paterno}")

    return maestro


@router.delete("/{maestro_id}", status_code=204)
def delete_maestro(maestro_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    maestro = db.query(Maestro).filter(Maestro.id == maestro_id).first()
    if not maestro:
        raise HTTPException(status_code=404, detail="Maestro no encontrado")

    maestro.is_deleted = True
    maestro.is_active = False

    if maestro.user_id:
        user = db.query(User).filter(User.id == maestro.user_id).first()
        if user:
            user.is_active = False

    db.commit()

    audit_log(db, _admin.id, "DELETE", "maestro", maestro.id,
              f"{_admin.username} eliminó al maestro {maestro.nombre} {maestro.apellido_paterno}")
