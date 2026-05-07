# GymControl API — Sesión 01 (2026-05-07)

## Stack

- **Python 3.13** / **FastAPI** / **SQLAlchemy 2.0** (ORM sync)
- **MySQL** en XAMPP (localhost:3306)
- **bcrypt** para hashing de passwords
- Servidor: `uvicorn` en `127.0.0.1:5000`

## Arranque rápido

```bash
cd c:\Users\CRamos.SPA09NMW000102\Desktop\GymControl_API
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 5000
```

## Base de datos

- **Nombre**: `gymcontrol` (ya existe en XAMPP MySQL)
- **Usuario**: `root` sin password
- **URL**: `mysql+pymysql://root:@localhost:3306/gymcontrol`
- **Driver**: PyMySQL (no psycopg2 — cambiamos de PostgreSQL a MySQL)
- Las tablas se crean automáticamente al iniciar (`Base.metadata.create_all` en lifespan)
- **SSL**: no requerido para local

## 11 Tablas creadas

| Tabla | Descripción |
|-------|-------------|
| `roles` | Catálogo: Admin (1), Maestro (2) — ya insertados manualmente |
| `generos` | Catálogo: pendiente llenar |
| `grupos_edad` | Catálogo: pendiente llenar |
| `estados_membresia` | Catálogo: activa, vencida, cancelada, etc. |
| `users` | Autenticación (admin + maestros). Columna: `username` (no email) |
| `maestros` | Perfil del maestro, FK a `users` (NULL si sin login) |
| `alumnos` | FK a `maestros.id` (RESTRICT), `generos.id`, `grupos_edad.id` |
| `tipos_membresia` | Catálogo de membresías con costo_base y duracion_dias |
| `membresias` | Historial por alumno, FK a `alumnos` (CASCADE), `tipos_membresia`, `estados_membresia` |
| `asistencias` | UNIQUE(alumno_id, fecha). FK a `alumnos` (CASCADE), `maestros`, `users` |
| `transacciones` | Ingresos y gastos unificados. FK opcionales a `membresias` y `alumnos` |

### Soft delete (`is_deleted`)

- `users`, `maestros`, `alumnos`, `tipos_membresia`

### Relación clave: maestro → alumno

- `alumnos.maestro_id` → `maestros.id`
- Para filtrar asistencias por maestro: `JOIN alumnos ON asistencias.alumno_id = alumnos.id WHERE alumnos.maestro_id = X`
- `asistencias` también tiene `maestro_id` desnormalizado para queries más rápidas

### Estados de membresía (on-read update)

- Al consultar membresías, el backend compara `fecha_vencimiento` con hoy. Si venció, actualiza `estado_id` antes de devolver la respuesta.

## Endpoints implementados

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Hola mundo |
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/users/` | Crear usuario (password hasheado con bcrypt) |
| GET | `/api/v1/users/` | Listar usuarios (`?include_deleted=true` para ver borrados) |
| GET | `/api/v1/users/{id}` | Obtener usuario por ID |
| PUT | `/api/v1/users/{id}` | Actualizar usuario (full_name, role_id, is_active) |
| DELETE | `/api/v1/users/{id}` | Soft delete (is_deleted=true, is_active=false) |

## Dependencias (requirements.txt)

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.3
pydantic-settings==2.7.0
python-dotenv==1.0.1
sqlalchemy==2.0.36
pymysql==1.1.1
bcrypt==5.0.0
```

**Nota**: passlib 1.7.4 es incompatible con bcrypt 5.x. Usamos bcrypt directo.

## Estructura del proyecto

```
GymControl_API/
├── app/
│   ├── main.py                    # App FastAPI + lifespan + routers
│   ├── api/
│   │   └── routes/
│   │       ├── health.py          # GET /api/v1/health
│   │       └── users.py           # CRUD /api/v1/users
│   ├── core/
│   │   ├── config.py              # Settings con pydantic-settings
│   │   ├── database.py            # Engine MySQL + SessionLocal + get_db()
│   │   └── security.py            # hash_password / verify_password (bcrypt)
│   ├── models/
│   │   ├── catalogs.py            # Rol, Genero, GrupoEdad, EstadoMembresia
│   │   ├── users.py               # User
│   │   ├── maestros.py            # Maestro
│   │   ├── alumnos.py             # Alumno
│   │   ├── membresias.py          # TipoMembresia, Membresia
│   │   ├── asistencias.py         # Asistencia
│   │   └── transacciones.py       # Transaccion
│   └── schemas/
│       └── users.py               # UserCreate, UserUpdate, UserResponse
├── .env                           # DATABASE_URL (MySQL local)
├── requirements.txt
└── SESION_01.md                   # Este archivo
```

## Pendiente próxima sesión

1. CRUD de `maestros`
2. CRUD de `alumnos`
3. CRUD de `tipos_membresia` + `membresias`
4. CRUD de `asistencias`
5. CRUD de `transacciones`
6. Llenar tablas catálogo (`generos`, `grupos_edad`, `estados_membresia`)
7. Lógica de actualización automática de `estado_id` en membresías vencidas
8. Sistema de autenticación (JWT) y autorización por roles
9. Métricas de profit mensual (ingresos - gastos)

## Decisiones importantes de esta sesión

- **PostgreSQL → MySQL**: Render daba timeout por DPI corporativo. Se usó XAMPP local.
- **`email` → `username`**: El usuario cambió la columna en `users` manualmente.
- **bcrypt directo** en vez de passlib (incompatibilidad de versiones).
- **ids BIGINT** en todas las tablas (decisión del usuario).
- **Tablas catálogo** con `TINYINT` autoincrement para roles, géneros, etc.
- **`transacciones` unificada** (ingresos + gastos en una tabla).
- No se usa `persona_especial` en alumnos, se reemplazó por `notas_medicas`.
