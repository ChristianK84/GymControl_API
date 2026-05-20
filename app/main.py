from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import alumnos, asistencias, auth, health, maestros, roles, users
from app.core.config import settings
from app.core.database import Base, engine
from app.models import (  # noqa: F401 — registra todos los modelos en Base.metadata
    Alumno,
    Asistencia,
    ContactoEmergencia,
    EstadoMembresia,
    FichaMedica,
    Maestro,
    Membresia,
    Rol,
    TipoMembresia,
    Transaccion,
    Tutor,
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(roles.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(alumnos.router, prefix=settings.API_V1_PREFIX)
app.include_router(maestros.router, prefix=settings.API_V1_PREFIX)
app.include_router(asistencias.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def hello_world():
    return {"message": "Hola mundo desde GymControl API"}
