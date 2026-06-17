from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models import Maestro, User

security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido o expirado")

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalido")

    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario desactivado")

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role_id != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accion solo para administradores")
    return current_user


def require_maestro(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role_id not in (1, 2):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accion solo para maestros y administradores")
    return current_user


def get_current_maestro(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Maestro | None:
    """Retorna el Maestro vinculado al usuario actual, o None si es admin (role_id=1)."""
    if current_user.role_id == 1:
        return None
    maestro = db.query(Maestro).filter(
        Maestro.user_id == current_user.id,
        Maestro.is_deleted == False,
        Maestro.is_active == True,
    ).first()
    if not maestro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes un perfil de maestro vinculado",
        )
    return maestro
