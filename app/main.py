from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

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

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(roles.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(alumnos.router, prefix=settings.API_V1_PREFIX)
app.include_router(maestros.router, prefix=settings.API_V1_PREFIX)
app.include_router(asistencias.router, prefix=settings.API_V1_PREFIX)


@app.get("/", response_class=HTMLResponse)
async def landing():
    return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GymControl API</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 40%, #16213e 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        }
        .container {
            text-align: center;
            padding: 3rem;
        }
        .logo {
            width: 140px;
            height: 140px;
            border-radius: 50%;
            object-fit: contain;
            background: rgba(255,255,255,0.06);
            backdrop-filter: blur(10px);
            padding: 20px;
            margin-bottom: 2rem;
            box-shadow: 0 0 60px rgba(99, 102, 241, 0.15);
            transition: transform 0.3s ease;
        }
        .logo:hover {
            transform: scale(1.05);
        }
        .logo-placeholder {
            display: inline-block;
            width: 140px;
            height: 140px;
            border-radius: 50%;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            margin-bottom: 2rem;
            box-shadow: 0 0 60px rgba(99, 102, 241, 0.25);
            line-height: 140px;
            font-size: 3rem;
            font-weight: 700;
            color: white;
            letter-spacing: 2px;
        }
        h1 {
            font-size: 2.4rem;
            font-weight: 700;
            color: #f1f5f9;
            letter-spacing: -0.5px;
            margin-bottom: 0.3rem;
        }
        .subtitle {
            font-size: 1.1rem;
            color: #94a3b8;
            font-weight: 400;
            margin-bottom: 0.8rem;
        }
        .version {
            display: inline-block;
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            padding: 0.25rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
            letter-spacing: 0.5px;
            margin-bottom: 1.5rem;
        }
        .footer {
            font-size: 0.8rem;
            color: #64748b;
            border-top: 1px solid rgba(255,255,255,0.06);
            padding-top: 1.5rem;
            margin-top: 0.5rem;
        }
        .status {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 2rem;
            font-size: 0.8rem;
            color: #22c55e;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background: #22c55e;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
    </style>
</head>
<body>
    <div class="container">
        <img src="/static/logo.jpg" alt="Katiras Gymnastics" class="logo"
             onerror="this.style.display='none'; this.nextElementSibling.style.display='inline-block';">
        <div class="logo-placeholder" style="display:none;">KG</div>

        <h1>GymControl API</h1>
        <p class="subtitle">Katiras Gymnastics</p>
        <span class="version">V1.0.0</span>

        <div class="status">
            <span class="status-dot"></span> En linea
        </div>

        <p class="footer">
            &copy; 2026 Katiras Gymnastics. Todos los derechos reservados.<br>
            <span style="font-size:0.7rem;color:#475569;">Marca registrada &reg;</span>
        </p>
    </div>
</body>
</html>
"""
