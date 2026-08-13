# GymControl API

API REST para gestión de gimnasios: control de alumnos, maestros, usuarios, asistencias, membresías y transacciones.

## Stack

- **Python 3.13** + **FastAPI**
- **SQLAlchemy 2.0** (ORM síncrono)
- **PostgreSQL** (Supabase)
- **bcrypt** — hashing de contraseñas
- **python-jose** — JWT (HS256)
- **pydantic-settings** — configuración por entorno
- **fpdf2** — generación de PDF con fuentes DejaVu embebidas
- **PyMuPDF** — embebido de firma digital en PDFs de reglamentos
- **Gmail API (OAuth2)** — envío de emails y recibos

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

## Módulo de Reglamentos y Firma Digital

- Admin sube PDFs de reglamentos a Cloudinary
- Campo `requires_firma` por documento: si es `false`, el tutor solo confirma lectura (sin canvas de firma)
- Generación de links JWT por alumno (expiración 30 días)
- Envío de emails a tutores con link de firma o lectura según corresponda
- Página HTML de firma/lectura servida por FastAPI
- Firma embebida en el PDF final vía PyMuPDF; lectura guarda `fecha_lectura`
- Flujo completo: upload → links → firma/lectura tutor → registro guardado

Rutas admin: `/api/v1/reglamentos/` · Rutas públicas: `/api/v1/reglamento/` · Lectura: `POST /api/v1/reglamento/leido`

## Recibos de membresía por WhatsApp

- `GET /api/v1/membresias/{id}/recibo.pdf` devuelve el PDF del recibo para compartir
- El frontend descarga el Blob y usa share nativo o `wa.me`

## Login flexible

- Username se normaliza a minúsculas y se hace `strip()`
- La contraseña se acepta tal cual o en minúsculas (fallback)
- Se mantiene el bloqueo tras intentos fallidos

## Licencia

Uso interno — Katiras Gymnastics
