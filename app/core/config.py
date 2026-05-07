from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "GymControl API"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "mysql+pymysql://root:@localhost:3306/gymcontrol"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
