import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.core.security import hash_password
from app.models import User
from app.schemas.users import PasswordResetResponse, UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="El username ya existe")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role_id=payload.role_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=list[UserResponse])
def list_users(
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    q = db.query(User)
    if not include_deleted:
        q = q.filter(User.is_deleted == False)
    return q.order_by(User.id).all()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if payload.username and payload.username != user.username:
        existing = db.query(User).filter(User.username == payload.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="El username ya existe")

    update_data = payload.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        update_data["password_hash"] = hash_password(update_data.pop("password"))
    elif "password" in update_data:
        del update_data["password"]

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
def reset_password(user_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    new_password = secrets.token_urlsafe(8)
    user.password_hash = hash_password(new_password)
    db.commit()

    return PasswordResetResponse(new_password=new_password)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_deleted = True
    user.is_active = False
    db.commit()
