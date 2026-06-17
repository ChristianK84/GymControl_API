import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


PASSWORD_PATTERN = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")
PASSWORD_ERROR = "La contraseña debe tener al menos 8 caracteres, incluir 1 mayúscula, 1 minúscula y 1 número"


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None
    role_id: int

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_PATTERN.match(v):
            raise ValueError(PASSWORD_ERROR)
        return v


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=150)
    password: Optional[str] = Field(default=None, min_length=8, max_length=128)
    full_name: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not PASSWORD_PATTERN.match(v):
            raise ValueError(PASSWORD_ERROR)
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role_id: int
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PasswordResetResponse(BaseModel):
    new_password: str
    message: str = "Contraseña restablecida exitosamente"
