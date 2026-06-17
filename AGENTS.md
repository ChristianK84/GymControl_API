# GymControl API — Notas del agente

API REST para gestión de gimnasio (alumnos, maestros, usuarios, asistencias, membresías, transacciones).

## Inicio rápido

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 5000
```

Servidor: FastAPI en puerto 5000 (no 8000). Todas las rutas bajo `/api/v1/`.

## Stack tecnológico

- **Python 3.13.5** / **FastAPI** / **SQLAlchemy 2.0** (ORM síncrono)
- **PostgreSQL** vía Supabase (`aws-1-us-west-2.pooler.supabase.com:6543`)
- **bcrypt** directo para hashing de passwords (NO usar passlib — incompatible con bcrypt 5.x)
- **python-jose** para JWT (HS256, expiración 60 min)
- **pydantic-settings** lee variables de `.env`

## Base de datos

- Las tablas se crean automáticamente al iniciar (`Base.metadata.create_all` en lifespan)
- Todos los IDs son `BIGINT`, los IDs de tablas catálogo son `TINYINT` autoincrement
- Soft delete vía flag `is_deleted` en: `users`, `maestros`, `alumnos`, `tipos_membresia`
- Estado de membresía: actualización on-read — compara `fecha_vencimiento` vs hoy, actualiza `estado_id` antes de responder

## Arquitectura

```
app/
├── main.py              # FastAPI app, lifespan, CORS (*), static mount, registro de routers
├── api/
│   ├── dependencies.py  # get_current_user, require_admin, require_maestro (role_id: 1=admin, 2=maestro)
│   └── routes/          # health, auth, users, roles, alumnos, maestros, asistencias, estados_membresia, tipos_membresia, membresias, transacciones
├── core/
│   ├── config.py        # Settings desde vars de entorno / .env
│   ├── database.py      # create_engine, SessionLocal, get_db, Base
│   └── security.py      # hash_password, verify_password, create_access_token, verify_token
├── models/              # Modelos SQLAlchemy (12 tablas)
└── schemas/             # Esquemas Pydantic request/response
```

## Autenticación y roles

- **Login**: `POST /api/v1/auth/login` → retorna JWT (`sub` = user_id string)
- **QR Scan**: `POST /api/v1/asistencias/scan` → `{alumno_id, maestro_id}` → validación completa de membresía + registro automático
- **Protección**: `Depends(get_current_user)` / `Depends(require_admin)` / `Depends(require_maestro)`
- role_id=1 → admin (todo), role_id=2 → maestro (limitado)

## Convenciones clave

- `username` (NO email) para inicio de sesión
- `asistencias` tiene `maestro_id` desnormalizado para consultas más rápidas
- `transacciones` unifica ingresos y gastos en una sola tabla
- Sin passlib; siempre usa `bcrypt.hashpw` / `bcrypt.checkpw` directamente

## Rutas disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/auth/login` | Inicio de sesión |
| CRUD | `/api/v1/users/` | Usuarios del sistema |
| CRUD | `/api/v1/roles/` | Catálogo de roles |
| CRUD | `/api/v1/alumnos/` | Alumnos |
| CRUD | `/api/v1/maestros/` | Maestros |
| CRUD | `/api/v1/asistencias/` | Asistencias (incluye scan QR) |
| CRUD | `/api/v1/membresias/` | Membresías de alumnos |
| CRUD | `/api/v1/tipos_membresia/` | Catálogo de tipos de membresía |
| CRUD | `/api/v1/estados_membresia/` | Catálogo de estados de membresía |
| CRUD | `/api/v1/transacciones/` | Ingresos y gastos |

## Despliegue

- **Railway** (builder Nixpacks)
- Start: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- Sin tests, sin CI, sin configuración de lint/typecheck
