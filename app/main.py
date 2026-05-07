from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, users
from app.core.config import settings
from app.core.database import Base, engine
from app.models import (  # noqa: F401 — registra todos los modelos en Base.metadata
    Alumno,
    Asistencia,
    EstadoMembresia,
    Genero,
    GrupoEdad,
    Maestro,
    Membresia,
    Rol,
    TipoMembresia,
    Transaccion,
    User,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def hello_world():
    return {"message": "Hola mundo desde GymControl API"}
