from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    APP_NAME: str = "GymControl API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = ""
    SECRET_KEY: str = Field(default="")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret(cls, v: str) -> str:
        if not v or len(v) < 32:
            raise ValueError(
                "SECRET_KEY debe tener al menos 32 caracteres. "
                "Verifica que el archivo .env exista y contenga una clave valida."
            )
        return v


settings = Settings()
