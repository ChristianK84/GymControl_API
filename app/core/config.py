from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "GymControl API"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "postgresql://postgres:KatirasGym.w.%21@db.ksyxiqwbkembvxjmxygu.supabase.co:5432/postgres"
    SECRET_KEY: str = "change-me-in-production-use-a-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
