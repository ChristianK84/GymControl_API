# GymControl API — Notas del agente

API REST para gestión de gimnasio (alumnos, maestros, usuarios, asistencias, membresías, transacciones, reglamentos con firma digital y versiones de app para OTA).

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
- **fpdf2** (2.8.1) — generación de PDF con fuentes DejaVu embebidas en `app/core/fonts/`
- **PyMuPDF** (1.25.5) — embebido de firma digital en PDFs de reglamentos
- **requests** (2.32.3) — HTTP client para subidas a Cloudinary
- **slowapi** (0.1.10) — rate limiting
- **Email**: Gmail API (OAuth2 + HTTPS) con stdlib (`urllib` + `email`) — cero dependencias externas

## Base de datos

- Las tablas se crean automáticamente al iniciar (`Base.metadata.create_all` en lifespan) junto con índices de rendimiento
- Todos los IDs son `BIGINT`, los IDs de tablas catálogo son `TINYINT` autoincrement
- Soft delete vía flag `is_deleted` en: `users`, `maestros`, `alumnos`, `tipos_membresia`, `reglamentos`, `firmas_reglamento`, `asistencias`, `transacciones`
- Estado de membresía: actualización on-read — compara `fecha_vencimiento` vs hoy, actualiza `estado_id` antes de responder

### Tablas (16)

| Tabla | Modelo | Descripción |
|-------|--------|-------------|
| `users` | User | Usuarios del sistema (admin/maestro) |
| `roles` | Rol | Catálogo: 1=Admin, 2=Maestro |
| `alumnos` | Alumno | Alumnos del gimnasio |
| `maestros` | Maestro | Instructores |
| `tutores` | Tutor | Padres/tutores de alumnos |
| `contacto_emergencia` | ContactoEmergencia | Contacto de emergencia |
| `fichas_medicas` | FichaMedica | Historial médico |
| `tipos_membresia` | TipoMembresia | Catálogo de planes (pricing complejo) |
| `membresias` | Membresia | Membresías activas de alumnos |
| `estados_membresia` | EstadoMembresia | Catálogo: Activa/Vencida/Cancelada/Pendiente |
| `asistencias` | Asistencia | Control de asistencia diaria |
| `transacciones` | Transaccion | Ingresos y gastos (tabla unificada) |
| `reglamentos` | Reglamento | Documentos/reglamentos PDF (Cloudinary) |
| `firmas_reglamento` | FirmaReglamento | Firmas digitales de tutores |
| `audit_logs` | AuditLog | Registro de auditoría |
| `app_versions` | AppVersion | Versiones de la app para OTA |

## Arquitectura

```
app/
├── main.py                 # FastAPI app, lifespan (create_all + índices), CORS (*), static mount, 16 routers
├── api/
│   ├── dependencies.py     # get_current_user, require_admin, require_maestro, get_current_maestro
│   └── routes/             # health, auth, users, roles, alumnos, maestros, asistencias, estados_membresia,
│                           # tipos_membresia, membresias, transacciones, reportes, audit_logs,
│                           # app_version, reglamentos (admin + público)
├── core/
│   ├── config.py           # Settings desde vars de entorno / .env
│   ├── database.py         # create_engine, SessionLocal, get_db, Base
│   ├── security.py         # bcrypt + JWT (iss/aud, token_version)
│   ├── audit.py            # Helper de auditoría (audit_log)
│   ├── limiter.py          # Rate limiting (slowapi, X-Forwarded-For)
│   ├── email.py            # Gmail OAuth2 API (enviar_recibo_email, enviar_email_html)
│   ├── pdf.py              # Recibo de membresía (fpdf2 + DejaVu)
│   ├── qr_utils.py         # Generación de QR PNG
│   ├── cloudinary_service.py # Upload de archivos a Cloudinary (preset "archivos")
│   └── fonts/              # DejaVuSans.ttf + DejaVuSans-Bold.ttf (Unicode PDF)
├── models/                 # 14 archivos, 17 modelos SQLAlchemy
└── schemas/                # 12 archivos, 37 esquemas Pydantic
```

## Autenticación y roles

- **Login**: `POST /api/v1/auth/login` → retorna JWT (`sub` = user_id string), con rate limit 10/min y bloqueo tras 5 intentos fallidos (15 min)
- **Refresh**: `POST /api/v1/auth-refresh` → renueva el token
- **QR Scan**: `POST /api/v1/asistencias/scan` → `{alumno_id, maestro_id}` → validación completa de membresía + registro automático
- **Protección**: `Depends(get_current_user)` / `Depends(require_admin)` / `Depends(require_maestro)`
- role_id=1 → admin (todo), role_id=2 → maestro (limitado a sus alumnos)

## Convenciones clave

- `username` (NO email) para inicio de sesión
- `asistencias` tiene `maestro_id` desnormalizado para consultas más rápidas
- `transacciones` unifica ingresos y gastos en una sola tabla
- Sin passlib; siempre usa `bcrypt.hashpw` / `bcrypt.checkpw` directamente
- Auditoría: toda operación de escritura registra en `audit_logs` con user, acción, entidad, entity_id y descripción legible

## Modelo `MembresiaResumen` + lógica Inscripción vs Membresía

### Schema (`app/schemas/alumnos.py`)

```python
class MembresiaResumen(BaseModel):
    is_active: bool          # estado_id == ACTIVA y no vencida
    fecha_vencimiento: date
    esta_vencida: bool       # hoy > fecha_vencimiento
    pagado: bool
    estado: str | None       # nombre del EstadoMembresia
```

### Inscripción vs Membresía

El endpoint `GET /alumnos/` retorna **dos** campos de resumen en cada alumno:

```python
class AlumnoResponse(BaseModel):
    ...
    inscripcion: MembresiaResumen | None = None  # tipo_membresia_id == 1
    membresia: MembresiaResumen | None = None    # tipo_membresia_id != 1
```

(Reemplaza el campo legacy `membresia_activa`, ya extinto.)

### Constantes en `app/api/routes/alumnos.py`

- `ACTIVA = 1`
- `PENDIENTE = 4`
- `TIPO_INSCRIPCION = 1`

### Helpers

```python
_build_membresia_resumen(m) -> MembresiaResumen
    # esta_vencida = hoy > m.fecha_vencimiento
    # is_active = m.estado_id == ACTIVA and not esta_vencida

_get_resumenes(alumno) -> tuple[MembresiaResumen | None, MembresiaResumen | None]
    # 1. Filtra alumno.membresias por estado_id in (ACTIVA, PENDIENTE)
    # 2. Separa: tipo_membresia_id == 1 → inscripciones; resto → membresias
    # 3. Toma max(fecha_vencimiento) en cada grupo → (inscripcion, membresia)
```

El `_alumno_base_query` hace `selectinload(Alumno.membresias).selectinload(Membresia.estado)` para evitar N+1.

### IDs reales de `estados_membresia` (validados)

| id | nombre | color |
|---|---|---|
| 1 | Activa | #22c55e |
| 2 | Vencida | #ef4444 |
| 3 | Cancelada | #6b7280 |
| 4 | Pendiente | #f59e0b |

## Rutas disponibles (~56 endpoints bajo `/api/v1/`)

| Módulo | Ruta | Acceso |
|--------|------|--------|
| Health | `GET /health` | Público |
| Auth | `POST /auth/login`, `POST /auth-refresh`, `POST /auth/logout` | Público / Autenticado |
| Users | CRUD `/users/` + `POST /users/{id}/reset-password` | Admin |
| Roles | `GET /roles/` | Autenticado |
| Alumnos | CRUD `/alumnos/` + `GET /alumnos/cumpleanos` + `POST /alumnos/{id}/enviar-qr` | Maestro (escritura), Autenticado (lectura) |
| Maestros | CRUD `/maestros/` | Admin (escritura), Autenticado (lectura) |
| Asistencias | CRUD `/asistencias/` + `POST /asistencias/scan` | Maestro |
| Membresías | CRUD `/membresias/` + `GET /membresias/impagas` + `POST /membresias/{id}/enviar-recibo` | Maestro |
| Tipos Membresía | CRUD `/tipos-membresia/` | Admin (escritura), Autenticado (lectura) |
| Estados Membresía | `GET /estados-membresia/` | Autenticado |
| Transacciones | CRUD `/transacciones/` + `GET /transacciones/reportes/profit` | Admin |
| Reportes | `GET /reportes/dashboard`, `GET /reportes/asistencias-por-maestro` | Admin |
| Audit Logs | `GET /audit-logs/` | Admin |
| App Version | `GET /app/version/{platform}` (público) + `PUT /app/version/{platform}` (admin) | Público / Admin |
| Reglamentos (admin) | `POST /reglamentos/`, `GET /reglamentos/`, `DELETE /reglamentos/{id}`, `PUT /reglamentos/{id}`, `POST /reglamentos/generar-links`, `GET /reglamentos/firmas`, `GET /reglamentos/firmas/{alumno_id}` | Admin |
| Reglamento (público) | `GET /reglamento/validar/{token}`, `POST /reglamento/firmar`, `GET /reglamento/firma` | Público (token JWT) |

## Reporte: Asistencias por Maestro (`GET /reportes/asistencias-por-maestro`)

Conteo de asistencias por maestro y semana ISO (lunes-domingo). Solo admin.

### Query params

| Param | Tipo | Default | Descripción |
|---|---|---|---|
| `fecha_inicio` | date | hace 8 semanas | Inicio del rango |
| `fecha_fin` | date | hoy | Fin del rango |
| `maestro_id` | int | — | Filtrar por un maestro |

### Lógica

- Cuenta solo `Asistencia.asistio == True`.
- Excluye maestros `is_deleted`/`is_active=False` y alumnos soft-deleted (vía JOIN).
- Agrupa por maestro y semana usando `date_trunc('week', fecha)` (PostgreSQL, lunes-domingo).
- Genera la lista de semanas ISO dentro del rango con `_generar_semanas_iso()` (helper en `routes/reportes.py`).
- Cada maestro devuelve `semanas: dict[semana_iso -> int]` (0 si no hubo asistencias) + `total_general`.

### Schemas (`app/schemas/reportes.py`)

- `SemanaAsistencias` — `{semana_iso, fecha_inicio, fecha_fin, total_asistencias}`
- `MaestroAsistencias` — `{maestro_id, maestro_nombre, maestro_apellido_paterno, total_general, semanas: dict}`
- `AsistenciasPorMaestroResponse` — `{fecha_inicio_global, fecha_fin_global, semanas[], maestros[]}`

## Módulo: Firma Digital de Reglamentos (IMPLEMENTADO)

### Visión general

El tutor recibe un link por correo → abre en navegador (sin login) → ve sus datos pre-cargados + PDF del reglamento → firma en canvas → se guarda PDF firmado en Cloudinary.

### Implementación

- **Rutas**: `app/api/routes/reglamentos.py` (957 líneas) con dos routers:
  - `router_admin` (prefix `/reglamentos`) — protegido
  - `router_public` (prefix `/reglamento`) — público, sin auth
- **JWT de links**: se genera inline en reglamentos.py (payload: alumno_id, tutor_id, reglamento_id, tipo="firma_reglamento", exp=+30d). Firmado con `SECRET_KEY`.
- **Página de firma**: HTML + JS vanilla servido con `HTMLResponse` desde FastAPI (sin Jinja). Incluye PDF embebido en `<iframe>` desde Cloudinary + canvas para firma (signature-pad vía CDN) + checkbox de aceptación.
- **Firma embedding**: PyMuPDF incrusta la imagen de la firma en el PDF final del lado del servidor. El PDF firmado se sube a Cloudinary y se actualiza el registro de `firmas_reglamento` (fecha_firma, URL, IP).
- **Email**: se envía con retry (3 intentos) vía `enviar_email_html`.

### Flujo completo

```
1. Admin sube PDF del reglamento → Cloudinary (preset "archivos")
2. Admin selecciona alumnos → "Generar links"
3. Backend recorre alumnos:
   a. Obtiene tutor vinculado
   b. Genera JWT (alumno_id, tutor_id, reglamento_id, exp=+30d)
   c. Guarda pre-registro en firmas_reglamento (sin fecha_firma)
   d. Envía email al tutor con link
4. Tutor abre link → se valida token (no expirado, no usado antes)
   → Se muestra página HTML con datos + PDF + canvas
5. Tutor firma → se sube:
   a. Imagen PNG de firma → Cloudinary
   b. Se genera PDF firmado (firma embebida al final con PyMuPDF)
   c. PDF firmado → Cloudinary
   d. Se actualiza firmas_reglamento (fecha_firma, URL, IP)
6. Admin ve estado en Angular (pendiente/firmado/expirado)
```

### Rutas API del módulo

| Método | Ruta | Acceso | Descripción |
|--------|------|--------|-------------|
| `POST` | `/api/v1/reglamentos/` | Admin | Crear reglamento (título, PDF URL, versión) |
| `GET` | `/api/v1/reglamentos/` | Autenticado | Listar reglamentos |
| `DELETE` | `/api/v1/reglamentos/{id}` | Admin | Soft delete |
| `PUT` | `/api/v1/reglamentos/{id}` | Admin | Actualizar reglamento |
| `POST` | `/api/v1/reglamentos/generar-links` | Admin | Generar JWT por alumno + enviar emails |
| `GET` | `/api/v1/reglamentos/firmas` | Autenticado | Listar firmas (filtros: reglamento_id, alumno_id, estado) |
| `GET` | `/api/v1/reglamentos/firmas/{alumno_id}` | Autenticado | Estado de firma de un alumno específico |
| `GET` | `/api/v1/reglamento/validar/{token}` | Público | Validar token JWT y retornar datos |
| `POST` | `/api/v1/reglamento/firmar` | Público | Recibir canvas firma en base64 + token |
| `GET` | `/api/v1/reglamento/firma` | Público | Servir página HTML de firma (?token=...) |

### Notas de implementación

- Los tokens de firma expiran a los 30 días (`expira_en`)
- Los links expirados o ya usados muestran mensaje de error en la página HTML
- El link enviado al tutor es: `{api}/api/v1/reglamento/firma?token=<JWT>`
- La firma se embebe en el PDF del lado del servidor (PyMuPDF) para consistencia
- El admin ve: alumno, tutor, fecha de envío, fecha de firma, PDF firmado (link), estado (pendiente/firmado/expirado)

## Recibo PDF + Email al crear membresía

Al crear una membresía (`POST /membresias/`) se ejecuta automáticamente:

1. Crea el registro en `membresias`
2. Crea un registro en `transacciones` (`tipo=1` ingreso, categoría "Membresía", vinculado a la membresía y alumno)
3. Genera PDF del recibo con logo y fuentes DejaVu (Ubuntu, macOS) o Helvetica (fallback)
4. Envía email al tutor con PDF adjunto (BackgroundTask — no bloquea la respuesta)

### Variables de entorno requeridas

| Variable | Valor |
|---|---|
| `GMAIL_CLIENT_ID` | Client ID de Google Cloud Console (OAuth 2.0 Web Application) |
| `GMAIL_CLIENT_SECRET` | Client Secret de Google Cloud Console |
| `GMAIL_REFRESH_TOKEN` | Refresh token OAuth2 (empieza con `1//`) |
| `EMAIL_FROM` | Gmail del gimnasio autorizado en OAuth consent screen |
| `LOGO_URL` | URL pública del logo en Cloudinary |

Setup: Google Cloud Console → habilitar Gmail API → OAuth consent screen (External, testing, scope `gmail.send`) → Web Application OAuth Client con redirect URI `https://developers.google.com/oauthplayground` → OAuth2 Playground para obtener refresh token.

### PDF del recibo

Generado con `app/core/pdf.py` usando `fpdf2`. Diseño profesional con:
- Logo del gimnasio (descargado de Cloudinary)
- Datos del alumno, tutor y membresía
- Tabla estilizada con costo, beca, fechas
- Fuente DejaVu con soporte Unicode (acentos, ñ, etc.)

### Email

Enviado con `app/core/email.py` usando Gmail API (OAuth2 + HTTPS). Contiene:
- Intercambio de refresh token → access token vía `oauth2.googleapis.com/token`
- Construcción de MIME multipart (HTML + PDF adjunto)
- POST a `gmail.googleapis.com/gmail/v1/users/me/messages/send`
- Cero dependencias externas (urllib + email stdlib)

## OTA Auto-Update

El backend sirve la versión de la app para que el frontend (Capacitor + `@capgo/capacitor-updater`) se actualice por aire.

- **Tabla**: `app_versions` (platform, version, version_code, bundle_url, release_notes, created_at)
- **GET** `/api/v1/app/version/{platform}` — público, devuelve la última versión publicada
- **PUT** `/api/v1/app/version/{platform}` — admin, publica una nueva versión (version, version_code, bundle_url, release_notes)
- El frontend consulta este endpoint al arrancar y descarga el bundle `.zip` si hay una versión más reciente

## Scripts

| Script | Propósito |
|--------|-----------|
| `scripts/import_alumnos.py` | Importar alumnos desde Excel (Google Forms). Dry-run por defecto. `--commit` para escribir. Requiere `openpyxl` |
| `scripts/seed_maestros.py` | Seed 2 admins (KOrtiz, Admin) + 6 maestros. Trunca `users` y `maestros` |
| `scripts/seed_tipos_membresia.py` | Upsert 5 tipos de membresía con pricing complejo |

## Despliegue

- **Render** (Web Service)
- Start: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`

## Dependencias (requirements.txt)

```
fastapi==0.115.6
fpdf2==2.8.1
qrcode==8.0
uvicorn[standard]==0.34.0
pydantic==2.10.3
pydantic-settings==2.7.0
python-dotenv==1.0.1
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
python-jose==3.4.0
bcrypt==5.0.0
slowapi==0.1.10
PyMuPDF==1.25.5
requests==2.32.3
```