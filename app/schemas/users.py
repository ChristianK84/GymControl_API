from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=150)
    password: str = Field(min_length=6, max_length=128)
    full_name: Optional[str] = None
    role_id: int


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=150)
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    full_name: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


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
