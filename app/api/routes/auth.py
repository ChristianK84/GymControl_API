from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import create_access_token, verify_password
from app.models import Maestro, User
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username, User.is_deleted == False).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")

    if user.locked_until:
        if user.locked_until > datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()
        db.refresh(user)

    if not verify_password(payload.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    token = create_access_token({"sub": str(user.id)})

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


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    audit_log(db, current_user.id, "LOGOUT", "auth", None, f"{current_user.username} cerró sesión")
    return {"message": "Sesión cerrada"}
