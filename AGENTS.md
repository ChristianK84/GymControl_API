# GymControl API — Agent instructions

## Quick start
```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 5000
```
Server: FastAPI on port 5000 (not 8000). All routes under `/api/v1/`.

## Tech stack
- **Python 3.13.5** / **FastAPI** / **SQLAlchemy 2.0** (sync ORM)
- **PostgreSQL** via Supabase (`aws-1-us-west-2.pooler.supabase.com:6543`)
- **bcrypt** directly for password hashing (do NOT use passlib — incompatible with bcrypt 5.x)
- **python-jose** for JWT (HS256, 60min expiry)
- **pydantic-settings** reads from `.env`

## Database
- Tables auto-create on startup (`Base.metadata.create_all` in `lifespan`)
- All IDs are `BIGINT`, catálogo (lookup) table IDs are `TINYINT` autoincrement
- Soft delete via `is_deleted` flag on: `users`, `maestros`, `alumnos`, `tipos_membresia`
- Membresía status: on-read update — compare `fecha_vencimiento` vs today, update `estado_id` before response

## Architecture
```
app/
├── main.py              # FastAPI app, lifespan, CORS (*), static mount, router registration
├── api/
│   ├── dependencies.py  # get_current_user, require_admin, require_maestro (role_id: 1=admin, 2=maestro)
│   └── routes/          # health, auth, users, roles, alumnos, maestros, asistencias, estados_membresia, tipos_membresia, membresias, transacciones
├── core/
│   ├── config.py        # Settings from env vars / .env
│   ├── database.py      # create_engine, SessionLocal, get_db, Base
│   └── security.py      # hash_password, verify_password, create_access_token, verify_token
├── models/              # SQLAlchemy models (12 tables)
└── schemas/             # Pydantic request/response schemas
```

## Auth & roles
- **Login**: `POST /api/v1/auth/login` → returns JWT (`sub`=user_id string)
- **QR Scan**: `POST /api/v1/asistencias/scan` → `{alumno_id, maestro_id}` → validación completa de membresía + registro automático
- **Protect**: `Depends(get_current_user)` / `Depends(require_admin)` / `Depends(require_maestro)`
- role_id=1 → admin (everything), role_id=2 → maestro (limited)

## Key conventions
- `username` NOT `email` for user login
- `asistencias` has denormalized `maestro_id` for faster queries
- `transacciones` unifies income + expense in one table (ingresos/gastos)
- No passlib; always use `bcrypt.hashpw`/`bcrypt.checkpw` directly

## Deploy
- **Railway** (Nixpacks builder)
- Start: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- No tests, no CI, no lint/typecheck config
