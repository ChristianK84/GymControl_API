from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "GymControl API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = ""
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
