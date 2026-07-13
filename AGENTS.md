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
- **fpdf2** (2.8.1) — generación de PDF con fuentes DejaVu embebidas en `app/core/fonts/`
- **smtplib** (stdlib) — envío de correos con PDF adjunto vía Gmail SMTP

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

## Recibo PDF + Email al crear membresía

Al crear una membresía (`POST /membresias/`) se ejecuta automáticamente:

1. Crea el registro en `membresias` (ya existía)
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

## Despliegue

- **Render** (Web Service)
- Start: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`

---

## Módulo: Firma Digital de Reglamentos (última sesión — pendiente implementar)

### Visión general

El tutor recibe un link por correo → abre en navegador (sin login) → ve sus datos pre-cargados + PDF del reglamento → firma en canvas → se guarda PDF firmado en Cloudinary.

### Tablas nuevas

**`reglamentos`**:
| Columna | Tipo | Notas |
|---------|------|-------|
| id | BIGINT PK | autoincrement |
| titulo | VARCHAR(200) | NO null |
| descripcion | TEXT | nullable |
| version | VARCHAR(20) | NO null (ej. "2025-1", "2026-1") |
| url_pdf_cloudinary | VARCHAR(500) | NO null |
| cloudinary_public_id | VARCHAR(200) | NO null |
| is_active | BOOLEAN | default true |
| is_deleted | BOOLEAN | default false |
| created_at | DATETIME | server default |
| updated_at | DATETIME | onupdate |

**`firmas_reglamento`**:
| Columna | Tipo | Notas |
|---------|------|-------|
| id | BIGINT PK | autoincrement |
| reglamento_id | BIGINT FK→reglamentos.id | NO null, RESTRICT |
| alumno_id | BIGINT FK→alumnos.id | NO null, CASCADE |
| tutor_id | BIGINT FK→tutores.id | NO null, CASCADE |
| token_usado | VARCHAR(500) | NO null (JWT usado) |
| url_pdf_firmado_cloudinary | VARCHAR(500) | nullable |
| cloudinary_public_id_firmado | VARCHAR(200) | nullable |
| fecha_firma | DATETIME | nullable (NULL = sin firmar) |
| ip_address | VARCHAR(45) | nullable |
| expira_en | DATETIME | NO null (created_at + 30 días) |
| is_deleted | BOOLEAN | default false |
| created_at | DATETIME | server default |

### Archivos a crear

| Archivo | Propósito |
|---------|-----------|
| `app/models/reglamentos.py` | Modelos `Reglamento` + `FirmaReglamento` |
| `app/schemas/reglamentos.py` | Schemas Create/Update/Response |
| `app/api/routes/reglamentos.py` | Todas las rutas del módulo |
| `app/core/cloudinary_service.py` | Subir/bajar archivos a Cloudinary (nuevo bucket para PDFs) |
| `app/core/jwt_reglamento.py` | Generar y validar tokens JWT para links de firma |
| `app/core/email_reglamento.py` | Enviar email estilizado con link de firma |
| `app/templates/firma_reglamento.html` | Página HTML estática para firma (CSS + JS vanilla) |

### Rutas API a crear

| Método | Ruta | Acceso | Descripción |
|--------|------|--------|-------------|
| `POST` | `/api/v1/reglamentos/upload` | Admin | Subir PDF del reglamento a Cloudinary |
| `GET` | `/api/v1/reglamentos/` | Admin | Listar reglamentos |
| `DELETE` | `/api/v1/reglamentos/{id}` | Admin | Soft delete |
| `POST` | `/api/v1/reglamentos/generar-links` | Admin | Generar JWT por alumno + enviar emails |
| `GET` | `/api/v1/reglamentos/firmas` | Admin | Listar todas las firmas (filtros) |
| `GET` | `/api/v1/reglamentos/firmas/{alumno_id}` | Admin | Estado de firma de un alumno específico |
| `GET` | `/api/v1/reglamento/firma` | Público | Servir página HTML de firma (?token=...) |
| `POST` | `/api/v1/reglamento/firmar` | Público | Recibir canvas firma en base64 + alumno_id + token |
| `GET` | `/api/v1/reglamento/validar/{token}` | Público | Validar token JWT y retornar datos |

### Token JWT para links

El link enviado al tutor es: `https://gymcontrol-api-sne4.onrender.com/api/v1/reglamento/firma?token=<JWT>`

Payload del JWT (firmado con SECRET_KEY del .env):
```json
{
  "alumno_id": 1,
  "tutor_id": 5,
  "reglamento_id": 2,
  "tipo": "firma_reglamento",
  "exp": 1743033600,
  "iat": 1740441600
}
```

Datos pre-cargados se obtienen del token + BD (no via URL params para evitar manipulación).

### Página de firma (`app/templates/firma_reglamento.html`)

Served by FastAPI with Jinja2 or static HTML + JS. Contains:
1. Encabezado con logo del gimnasio
2. Info del tutor y alumno (pre-cargados del token)
3. Título del reglamento
4. PDF embebido en `<iframe>` (desde Cloudinary)
5. Canvas para firma (signature-pad JS vanilla)
6. Checkbox de aceptación
7. Botón "Firmar y Aceptar"
8. Envía: canvas.toDataURL('image/png') base64 + PDF original → se embebe firma al final del PDF (con pdf-lib o similar server-side a través de Python) y se sube a Cloudinary

### Flujo completo

```
1. Admin sube PDF del reglamento → Cloudinary (nuevo bucket pdfs_reglamentos/)
2. Admin selecciona alumnos → "Generar links"
3. Backend recorre alumnos:
   a. Obtiene tutor vinculado
   b. Genera JWT (alumno_id, tutor_id, reglamento_id, exp=+30d)
   c. Guarda pre-registro en firmas_reglamento (sin fecha_firma)
   d. Envía email al tutor con link
4. Tutor abre link → se valida token (no expirado, no usado antes)
   → Se muestra página HTML con datos + PDF + canvas
5. Tutor firma → se sube:
   a. Imagen PNG de firma → Cloudinary (firmas/)
   b. Se genera PDF firmado (firma embebida al final con PyMuPDF/fpdf2)
   c. PDF firmado → Cloudinary (pdfs_firmados/)
   d. Se actualiza firmas_reglamento (fecha_firma, URL, IP)
6. Se envía email al tutor con copia del PDF firmado
7. Admin ve estado en Angular (agregar firma_reglamento a FirmaReglamentoResponse)
```

### Dependencias nuevas

- `cloudinary` — SDK Python para subir PDFs firmados
- `PyMuPDF` (fitz) o `reportlab` — para embeber imagen de firma en el PDF
- python-jose (ya instalado) — para tokens JWT de links

### Notas de implementación

- El router `reglamentos.py` se registra con dos prefijos: `/api/v1/reglamentos` (protegido) y `/api/v1/reglamento` (público, sin auth)
- La página HTML se sirve con `HTMLResponse` desde FastAPI (sin Jinja — HTML estático con interpolación JS)
- signature-pad se carga vía CDN (no npm) para la página estática
- La firma se embebe en el PDF del lado del servidor (PyMuPDF) para consistencia
- Los links expirados o ya usados muestran mensaje de error en la página HTML
- El admin debe ver: alumno, tutor, fecha de envío, fecha de firma, PDF firmado (link), estado (pendiente/firmado/expirado)
