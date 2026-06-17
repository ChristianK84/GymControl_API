from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    full_name: str | None
    role_id: int
    maestro_id: int | None = None
