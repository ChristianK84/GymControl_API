from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.routes import alumnos, asistencias, audit_logs, auth, estados_membresia, health, maestros, membresias, reportes, roles, tipos_membresia, transacciones, users
from sqlalchemy import text

from app.core.config import settings
from app.core.database import Base, engine
from app.core.limiter import limiter
from app.models import (  # noqa: F401 — registra todos los modelos en Base.metadata
    Alumno,
    Asistencia,
    AuditLog,
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


_INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_membresias_fecha_vencimiento ON membresias(fecha_vencimiento)",
    "CREATE INDEX IF NOT EXISTS idx_membresias_alumno_id ON membresias(alumno_id)",
    "CREATE INDEX IF NOT EXISTS idx_transacciones_fecha ON transacciones(fecha)",
    "CREATE INDEX IF NOT EXISTS idx_asistencias_maestro_id ON asistencias(maestro_id)",
    "CREATE INDEX IF NOT EXISTS idx_alumnos_maestro_id ON alumnos(maestro_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_asistencia_diaria ON asistencias (alumno_id, DATE(fecha))",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            for stmt in _INDICES:
                conn.execute(text(stmt))
            conn.commit()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Error al crear indices en startup: %s", exc)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_logs.router, prefix=settings.API_V1_PREFIX)
app.include_router(roles.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(alumnos.router, prefix=settings.API_V1_PREFIX)
app.include_router(maestros.router, prefix=settings.API_V1_PREFIX)
app.include_router(asistencias.router, prefix=settings.API_V1_PREFIX)
app.include_router(estados_membresia.router, prefix=settings.API_V1_PREFIX)
app.include_router(tipos_membresia.router, prefix=settings.API_V1_PREFIX)
app.include_router(membresias.router, prefix=settings.API_V1_PREFIX)
app.include_router(reportes.router, prefix=settings.API_V1_PREFIX)
app.include_router(transacciones.router, prefix=settings.API_V1_PREFIX)


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
            background: linear-gradient(160deg, #0a0a0a 0%, #1a1a1a 50%, #0d0d0d 100%);
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
            width: 150px;
            height: 150px;
            border-radius: 50%;
            object-fit: contain;
            background: rgba(255,255,255,0.04);
            backdrop-filter: blur(10px);
            padding: 18px;
            margin-bottom: 2rem;
            box-shadow: 0 0 60px rgba(220, 38, 38, 0.2);
            transition: transform 0.3s ease;
        }
        .logo:hover {
            transform: scale(1.05);
        }
        .logo-placeholder {
            display: inline-block;
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: linear-gradient(135deg, #dc2626, #991b1b);
            margin-bottom: 2rem;
            box-shadow: 0 0 60px rgba(220, 38, 38, 0.35);
            line-height: 150px;
            font-size: 3rem;
            font-weight: 700;
            color: white;
            letter-spacing: 2px;
        }
        .divider {
            width: 60px;
            height: 3px;
            background: linear-gradient(90deg, transparent, #dc2626, transparent);
            margin: 0 auto 1rem;
        }
        h1 {
            font-size: 2.4rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.5px;
            margin-bottom: 0.3rem;
        }
        .subtitle {
            font-size: 1.1rem;
            color: #a3a3a3;
            font-weight: 400;
            margin-bottom: 0.8rem;
        }
        .version {
            display: inline-block;
            background: rgba(220, 38, 38, 0.12);
            color: #f87171;
            border: 1px solid rgba(220, 38, 38, 0.25);
            padding: 0.25rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
            letter-spacing: 0.5px;
            margin-bottom: 1.5rem;
        }
        .footer {
            font-size: 0.8rem;
            color: #737373;
            border-top: 1px solid rgba(255,255,255,0.08);
            padding-top: 1.5rem;
            margin-top: 0.5rem;
        }
        .status {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 2rem;
            font-size: 0.8rem;
            color: #dc2626;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background: #dc2626;
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
        <img src="/static/logo.jpeg" alt="Katiras Gymnastics" class="logo"
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
