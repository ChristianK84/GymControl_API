from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Maestro, User
from app.schemas.auth import ChangePasswordPayload, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

_PLACEHOLDER_HASH = hash_password("placeholder")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        func.lower(User.username) == payload.username.strip().lower(),
        User.is_deleted == False,
    ).first()

    if not user or not user.is_active:
        verify_password(payload.password, _PLACEHOLDER_HASH)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")

    if user.locked_until:
        if user.locked_until > datetime.now(timezone.utc):
            verify_password(payload.password, _PLACEHOLDER_HASH)
            minutos = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60) + 1
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Cuenta bloqueada. Intente de nuevo en {minutos} minuto(s)."
            )
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()
        db.refresh(user)

    submitted_password = payload.password.strip()
    password_matches = (
        verify_password(submitted_password, user.password_hash)
        or verify_password(submitted_password.lower(), user.password_hash)
        or verify_password(submitted_password.upper(), user.password_hash)
        or verify_password(submitted_password.capitalize(), user.password_hash)
    )
    if not password_matches:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.LOGIN_MAX_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    token = create_access_token({"sub": str(user.id), "tv": user.token_version})

    maestro_id = None
    if user.role_id == 2:
        maestro = db.query(Maestro).filter(
            Maestro.user_id == user.id,
            Maestro.is_deleted == False,
            Maestro.is_active == True,
        ).first()
        if maestro:
            maestro_id = maestro.id

    audit_log(db, user.id, "LOGIN", "auth", None, f"{user.username} inició sesión")

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role_id=user.role_id,
        maestro_id=maestro_id,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token = create_access_token({"sub": str(current_user.id), "tv": current_user.token_version})
    maestro_id = None
    if current_user.role_id == 2:
        maestro = db.query(Maestro).filter(
            Maestro.user_id == current_user.id,
            Maestro.is_deleted == False,
            Maestro.is_active == True,
        ).first()
        if maestro:
            maestro_id = maestro.id
    return TokenResponse(
        access_token=token,
        user_id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        role_id=current_user.role_id,
        maestro_id=maestro_id,
    )


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit_log(db, current_user.id, "LOGOUT", "auth", None, f"{current_user.username} cerró sesión")
    return {"message": "Sesión cerrada"}


@router.post("/change-password")
def change_password(
    payload: ChangePasswordPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="La contraseña actual es incorrecta")

    current_user.password_hash = hash_password(payload.new_password)
    current_user.token_version += 1
    db.commit()

    audit_log(db, current_user.id, "UPDATE", "usuario", current_user.id,
              f"{current_user.username} cambió su contraseña")

    return {"message": "Contraseña actualizada exitosamente"}
