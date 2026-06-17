# GymControl API

API REST para gestión de gimnasios: control de alumnos, maestros, usuarios, asistencias, membresías y transacciones.

## Stack

- **Python 3.13** + **FastAPI**
- **SQLAlchemy 2.0** (ORM síncrono)
- **PostgreSQL** (Supabase)
- **bcrypt** — hashing de contraseñas
- **python-jose** — JWT (HS256)
- **pydantic-settings** — configuración por entorno

## Inicio rápido

```bash
# Instalar dependencias
pip install -r requirements.txt

# Copiar y configurar variables de entorno
cp .env.example .env

# Iniciar servidor de desarrollo
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 5000
```

La API estará disponible en `http://localhost:5000/api/v1/`.

Documentación interactiva: `http://localhost:5000/docs`

## Variables de entorno

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | URL de conexión a PostgreSQL |
| `SECRET_KEY` | Clave secreta para firmar JWT |

## Requisitos

Ver `requirements.txt` para dependencias completas.

## Frontend

La interfaz de usuario vive en el repositorio [`GymControl`](https://github.com/CRamos/GymControl) (Angular + Ionic + Electron).

## Licencia

Uso interno — Katiras Gymnastics
