import io
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_user, require_admin
from app.core.audit import audit_log
from app.core.cloudinary_service import upload_file
from app.core.config import settings
from app.core.database import get_db
from app.core.email import enviar_email_html
from app.models import Alumno, Maestro, Tutor, User
from app.models.reglamentos import FirmaReglamento, Reglamento
from app.schemas.reglamentos import (
    FirmaReglamentoResponse,
    FirmarPayload,
    GenerarLinksPayload,
    GenerarLinksResponse,
    ReglamentoCreate,
    ReglamentoResponse,
    ReglamentoUpdate,
    ValidarTokenResponse,
)

logger = logging.getLogger(__name__)

TOKEN_EXPIRY_DAYS = 30
LOGO_URL = settings.LOGO_URL

router_admin = APIRouter(prefix="/reglamentos", tags=["reglamentos"])
router_public = APIRouter(prefix="/reglamento", tags=["reglamento (publico)"])


def _generar_token(
    alumno_id: int, tutor_id: int, reglamento_id: int
) -> tuple[str, datetime]:
    expira = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS)
    payload = {
        "alumno_id": alumno_id,
        "tutor_id": tutor_id,
        "reglamento_id": reglamento_id,
        "tipo": "firma_reglamento",
        "exp": expira,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expira


def _decodificar_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("tipo") != "firma_reglamento":
            return None
        return payload
    except JWTError:
        return None


def _obtener_estado(firma: FirmaReglamento) -> str:
    if firma.fecha_firma:
        return "firmado"
    if firma.expira_en.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return "expirado"
    return "pendiente"


# ──────────────────── Admin routes ────────────────────


@router_admin.post("/", response_model=ReglamentoResponse, status_code=201)
def crear_reglamento(
    payload: ReglamentoCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    reg = Reglamento(**payload.model_dump())
    db.add(reg)
    db.commit()
    db.refresh(reg)
    audit_log(db, _admin.id, "CREATE", "reglamento", reg.id, f"Reglamento {reg.titulo} v{reg.version}")
    return reg


@router_admin.get("/", response_model=list[ReglamentoResponse])
def listar_reglamentos(
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    q = db.query(Reglamento)
    if not include_deleted:
        q = q.filter(Reglamento.is_deleted == False)
    return q.order_by(Reglamento.created_at.desc()).all()


@router_admin.delete("/{reglamento_id}", status_code=204)
def eliminar_reglamento(
    reglamento_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    reg = db.query(Reglamento).filter(Reglamento.id == reglamento_id, Reglamento.is_deleted == False).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Reglamento no encontrado")
    reg.is_deleted = True
    db.commit()
    audit_log(db, _admin.id, "DELETE", "reglamento", reg.id, f"Eliminado reglamento {reg.titulo}")


@router_admin.put("/{reglamento_id}", response_model=ReglamentoResponse)
def actualizar_reglamento(
    reglamento_id: int,
    payload: ReglamentoUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    reg = db.query(Reglamento).filter(Reglamento.id == reglamento_id, Reglamento.is_deleted == False).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Reglamento no encontrado")

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No se enviaron campos para actualizar")

    for key, value in update_data.items():
        setattr(reg, key, value)

    db.commit()
    db.refresh(reg)
    audit_log(db, _admin.id, "UPDATE", "reglamento", reg.id, f"Actualizado reglamento {reg.titulo}")
    return reg


@router_admin.post("/generar-links", response_model=GenerarLinksResponse)
def generar_links(
    payload: GenerarLinksPayload,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    reglamento = (
        db.query(Reglamento)
        .filter(Reglamento.id == payload.reglamento_id, Reglamento.is_deleted == False)
        .first()
    )
    if not reglamento:
        raise HTTPException(status_code=404, detail="Reglamento no encontrado")

    alumnos = (
        db.query(Alumno)
        .options(joinedload(Alumno.tutor))
        .filter(Alumno.id.in_(payload.alumno_ids), Alumno.is_deleted == False)
        .all()
    )
    if not alumnos:
        raise HTTPException(status_code=400, detail="No se encontraron alumnos válidos")

    base_url = str(request.base_url).rstrip("/")
    enviados = 0
    emails_data = []

    for alumno in alumnos:
        if not alumno.tutor:
            logger.warning("Alumno %d no tiene tutor, saltando", alumno.id)
            continue

        alumno_id = alumno.id
        tutor_id = alumno.tutor.id
        reglamento_id = reglamento.id

        token, expira = _generar_token(alumno_id, tutor_id, reglamento_id)

        firma_existente = (
            db.query(FirmaReglamento)
            .filter(
                FirmaReglamento.reglamento_id == reglamento_id,
                FirmaReglamento.alumno_id == alumno_id,
                FirmaReglamento.is_deleted == False,
            )
            .first()
        )
        if firma_existente:
            if firma_existente.fecha_firma:
                logger.info("Alumno %d ya firmó, saltando", alumno_id)
                continue
            token_usado_anterior = firma_existente.token_usado
            payload_viejo = _decodificar_token(token_usado_anterior)
            if payload_viejo:
                exp_viejo = payload_viejo.get("exp")
                if isinstance(exp_viejo, (int, float)):
                    viejo_ts = datetime.fromtimestamp(exp_viejo, tz=timezone.utc)
                    if viejo_ts > datetime.now(timezone.utc):
                        token = token_usado_anterior
                        expira = viejo_ts
                        logger.info("Alumno %d ya tenía token vigente, reutilizando", alumno_id)
            firma_existente.token_usado = token
            firma_existente.expira_en = expira
        else:
            nueva_firma = FirmaReglamento(
                reglamento_id=reglamento_id,
                alumno_id=alumno_id,
                tutor_id=tutor_id,
                token_usado=token,
                expira_en=expira,
            )
            db.add(nueva_firma)

        db.commit()

        link = f"{base_url}/api/v1/reglamento/firma?token={token}"

        tutor_obj = alumno.tutor
        nombre_tutor = f"{tutor_obj.nombre} {tutor_obj.apellido_paterno}"
        email_tutor = tutor_obj.email

        if email_tutor:
            emails_data.append({
                'email': email_tutor,
                'nombre_tutor': nombre_tutor,
                'nombre_alumno': f"{alumno.nombrecompleto} {alumno.apellido_paterno}",
                'link': link,
            })
            enviados += 1

    if emails_data:
        background_tasks.add_task(enviar_lote, emails_data, reglamento.titulo, reglamento.version)

    audit_log(
        db, _admin.id, "GENERAR_LINKS", "reglamento", reglamento.id,
        f"Generados links para {len(alumnos)} alumnos, {enviados} emails intentados"
    )
    return GenerarLinksResponse(enviados=enviados, total=len(alumnos))


def enviar_lote(emails_data, reg_titulo, reg_version):
    try:
        logo_url = LOGO_URL
        fallidos = list(emails_data)
        enviados = []

        for attempt in range(3):
            if not fallidos:
                break
            if attempt > 0:
                time.sleep(0.5)
                logger.info("Reintento %d/2 para %d emails...", attempt, len(fallidos))

            batch = list(fallidos)
            fallidos = []

            for i, data in enumerate(batch):
                if i > 0:
                    time.sleep(0.5)

                html = f"""
                <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
                    <div style="text-align:center;padding:20px 0;">
                        <img src="{logo_url}" alt="Katira's Gymnastics" style="width:120px;">
                        <h1 style="color:#0d47a1;margin:10px 0 0;">Katira's Gymnastics</h1>
                    </div>
                    <div style="background:#f5f5f5;border-radius:8px;padding:25px;margin:15px 0;">
                        <p style="font-size:16px;color:#333;">Hola <strong>{data['nombre_tutor']}</strong>,</p>
                        <p style="font-size:14px;color:#555;">
                            Te informamos que el reglamento interno de nuestra academia ha sido actualizado
                            y necesita ser firmado por el tutor del alumno(a).
                        </p>
                        <p style="font-size:14px;color:#555;">
                            <strong>Alumno(a):</strong> {data['nombre_alumno']}<br>
                            <strong>Documento:</strong> {reg_titulo} (v{reg_version})
                        </p>
                        <div style="text-align:center;margin:25px 0;">
                            <a href="{data['link']}" style="display:inline-block;background:#0d47a1;color:white;padding:14px 32px;border-radius:6px;text-decoration:none;font-size:16px;font-weight:600;">
                                Firmar Reglamento
                            </a>
                        </div>
                        <p style="font-size:12px;color:#999;">
                            Este link expirar&aacute; en 30 d&iacute;as. Si no puede acceder, copie y pegue
                            el siguiente enlace en su navegador:<br>
                            <span style="word-break:break-all;color:#666;">{data['link']}</span>
                        </p>
                    </div>
                    <p style="text-align:center;font-size:11px;color:#aaa;">
                        Katira's Gymnastics &mdash; Este es un mensaje autom&aacute;tico.
                    </p>
                </div>
                """

                ok = enviar_email_html(
                    destinatario_email=data['email'],
                    asunto=f"Katira's Gymnastics - Firma de Reglamento ({data['nombre_alumno']})",
                    cuerpo_html=html,
                )

                if ok:
                    enviados.append(data)
                    logger.info("[Pass %d] Email enviado a %s", attempt + 1, data['email'])
                else:
                    fallidos.append(data)
                    logger.warning("[Pass %d] Fallo envio a %s", attempt + 1, data['email'])

        total = len(enviados) + len(fallidos)
        logger.info("=== RESUMEN ENVIO MASIVO === Enviados: %d/%d, Fallidos: %d", len(enviados), total, len(fallidos))
        for f in fallidos:
            logger.warning("FALLO FINAL: %s (%s)", f['email'], f['nombre_tutor'])
    except Exception as e:
        logger.error("Error critico en enviar_lote: %s", e, exc_info=True)


@router_admin.get("/firmas", response_model=list[FirmaReglamentoResponse])
def listar_firmas(
    reglamento_id: Optional[int] = Query(None),
    alumno_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    q = (
        db.query(FirmaReglamento)
        .options(
            joinedload(FirmaReglamento.alumno),
            joinedload(FirmaReglamento.tutor),
        )
        .filter(FirmaReglamento.is_deleted == False)
    )

    if reglamento_id:
        q = q.filter(FirmaReglamento.reglamento_id == reglamento_id)
    if alumno_id:
        q = q.filter(FirmaReglamento.alumno_id == alumno_id)

    firmas = q.order_by(FirmaReglamento.created_at.desc()).all()

    result = []
    for f in firmas:
        est = _obtener_estado(f)
        if estado and est != estado:
            continue
        alumno_nombre = f"{f.alumno.nombrecompleto} {f.alumno.apellido_paterno}" if f.alumno else None
        tutor_nombre = f"{f.tutor.nombre} {f.tutor.apellido_paterno}" if f.tutor else None

        result.append(
            FirmaReglamentoResponse(
                id=f.id,
                reglamento_id=f.reglamento_id,
                alumno_id=f.alumno_id,
                tutor_id=f.tutor_id,
                alumno_nombre=alumno_nombre,
                tutor_nombre=tutor_nombre,
                url_pdf_firmado_cloudinary=f.url_pdf_firmado_cloudinary,
                fecha_firma=f.fecha_firma,
                expira_en=f.expira_en,
                estado=est,
                created_at=f.created_at,
            )
        )
    return result


@router_admin.get("/firmas/{alumno_id}", response_model=list[FirmaReglamentoResponse])
def firmas_por_alumno(
    alumno_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    firmas = (
        db.query(FirmaReglamento)
        .options(joinedload(FirmaReglamento.alumno), joinedload(FirmaReglamento.tutor))
        .filter(
            FirmaReglamento.alumno_id == alumno_id,
            FirmaReglamento.is_deleted == False,
        )
        .all()
    )

    result = []
    for f in firmas:
        est = _obtener_estado(f)
        alumno_nombre = f"{f.alumno.nombrecompleto} {f.alumno.apellido_paterno}" if f.alumno else None
        tutor_nombre = f"{f.tutor.nombre} {f.tutor.apellido_paterno}" if f.tutor else None

        result.append(
            FirmaReglamentoResponse(
                id=f.id,
                reglamento_id=f.reglamento_id,
                alumno_id=f.alumno_id,
                tutor_id=f.tutor_id,
                alumno_nombre=alumno_nombre,
                tutor_nombre=tutor_nombre,
                url_pdf_firmado_cloudinary=f.url_pdf_firmado_cloudinary,
                fecha_firma=f.fecha_firma,
                expira_en=f.expira_en,
                estado=est,
                created_at=f.created_at,
            )
        )
    return result


# ──────────────────── Public routes (no auth) ────────────────────


@router_public.get("/validar/{token}", response_model=ValidarTokenResponse)
def validar_token(token: str, db: Session = Depends(get_db)):
    payload = _decodificar_token(token)
    if not payload:
        return ValidarTokenResponse(valido=False, mensaje="El enlace no es válido o está corrupto.")

    alumno_id = payload.get("alumno_id")
    reglamento_id = payload.get("reglamento_id")

    alumno = db.query(Alumno).filter(Alumno.id == alumno_id, Alumno.is_deleted == False).first()
    if not alumno:
        return ValidarTokenResponse(valido=False, mensaje="Alumno no encontrado.")

    tutor = db.query(Tutor).filter(Tutor.alumno_id == alumno_id).first()
    if not tutor:
        return ValidarTokenResponse(valido=False, mensaje="Tutor no encontrado.")

    reglamento = (
        db.query(Reglamento)
        .filter(Reglamento.id == reglamento_id, Reglamento.is_deleted == False)
        .first()
    )
    if not reglamento:
        return ValidarTokenResponse(valido=False, mensaje="Reglamento no encontrado.")

    firma = (
        db.query(FirmaReglamento)
        .filter(
            FirmaReglamento.token_usado == token,
            FirmaReglamento.is_deleted == False,
        )
        .first()
    )

    if not firma:
        return ValidarTokenResponse(valido=False, mensaje="Registro de firma no encontrado.")

    exp = payload.get("exp")
    if isinstance(exp, (int, float)):
        exp_date = datetime.fromtimestamp(exp, tz=timezone.utc)
        if exp_date < datetime.now(timezone.utc):
            return ValidarTokenResponse(
                valido=False, expirado=True, mensaje="Este enlace ha expirado (vigencia de 30 días). Contacta a la academia para obtener un nuevo enlace."
            )

    if firma.fecha_firma:
        return ValidarTokenResponse(
            valido=False,
            ya_firmado=True,
            alumno_nombre=f"{alumno.nombrecompleto} {alumno.apellido_paterno}",
            tutor_nombre=f"{tutor.nombre} {tutor.apellido_paterno}",
            titulo_reglamento=reglamento.titulo,
            version=reglamento.version,
            mensaje="Este reglamento ya fue firmado anteriormente.",
        )

    return ValidarTokenResponse(
        valido=True,
        alumno_nombre=f"{alumno.nombrecompleto} {alumno.apellido_paterno}",
        tutor_nombre=f"{tutor.nombre} {tutor.apellido_paterno}",
        tutor_telefono=tutor.telefono,
        tutor_email=tutor.email,
        titulo_reglamento=reglamento.titulo,
        version=reglamento.version,
        url_pdf=reglamento.url_pdf_cloudinary,
    )


@router_public.post("/firmar")
def procesar_firma(
    payload: FirmarPayload,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    token = payload.token
    firma_base64 = payload.firma_base64

    token_data = _decodificar_token(token)
    if not token_data:
        return {"exito": False, "mensaje": "El enlace no es válido o está corrupto."}

    alumno_id = token_data.get("alumno_id")
    reglamento_id = token_data.get("reglamento_id")

    firma = (
        db.query(FirmaReglamento)
        .filter(FirmaReglamento.token_usado == token, FirmaReglamento.is_deleted == False)
        .first()
    )
    if not firma:
        return {"exito": False, "mensaje": "Registro de firma no encontrado."}
    if firma.fecha_firma:
        return {"exito": False, "mensaje": "Este reglamento ya fue firmado anteriormente."}
    if firma.expira_en.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return {"exito": False, "mensaje": "El enlace ha expirado."}

    alumno = db.query(Alumno).filter(Alumno.id == alumno_id, Alumno.is_deleted == False).first()
    tutor = db.query(Tutor).filter(Tutor.alumno_id == alumno_id).first()
    reglamento = (
        db.query(Reglamento)
        .filter(Reglamento.id == reglamento_id, Reglamento.is_deleted == False)
        .first()
    )

    if not all([alumno, tutor, reglamento]):
        return {"exito": False, "mensaje": "Datos no encontrados."}

    try:
        header = "data:image/png;base64,"
        if firma_base64.startswith(header):
            firma_base64 = firma_base64[len(header):]

        sig_bytes = __import__("base64").b64decode(firma_base64)

        pdf_response = requests.get(reglamento.url_pdf_cloudinary, timeout=30)
        pdf_response.raise_for_status()
        pdf_bytes = io.BytesIO(pdf_response.content)

        try:
            import fitz
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            last_page = doc[-1]
            page_width = last_page.rect.width

            sig_pixmap = fitz.Pixmap(sig_bytes)
            sig_scale = 400 / sig_pixmap.width if sig_pixmap.width > 400 else 1.0
            sig_display_width = sig_pixmap.width * sig_scale * 72 / 200
            sig_x = (page_width - sig_display_width) / 2
            y_bottom = last_page.rect.height - 50
            y_top = y_bottom - 100

            sig_rect = fitz.Rect(sig_x, y_top, sig_x + sig_display_width, y_bottom)
            last_page.insert_image(sig_rect, stream=sig_bytes)

            text_x = sig_x + 2
            last_page.insert_text(
                fitz.Point(text_x, y_bottom + 13),
                f"Firmado por: {tutor.nombre} {tutor.apellido_paterno}",
                fontsize=10,
                color=(0.2, 0.2, 0.2),
            )
            last_page.insert_text(
                fitz.Point(text_x, y_bottom + 25),
                f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                fontsize=9,
                color=(0.4, 0.4, 0.4),
            )

            final_bytes = doc.write()
            doc.close()
        except ImportError:
            from fpdf import FPDF
            sig_pdf = FPDF()
            sig_pdf.add_page()
            sig_img = io.BytesIO(sig_bytes)
            sig_pdf.image(sig_img, x=10, y=10, w=80)
            sig_pdf.set_font("Helvetica", "", 10)
            sig_pdf.cell(0, 10, text=f"Firmado por: {tutor.nombre} {tutor.apellido_paterno}", new_x="LMARGIN", new_y="NEXT")
            sig_pdf.cell(0, 10, text=f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", new_x="LMARGIN", new_y="NEXT")
            sig_page_bytes = sig_pdf.output()

            final_bytes = pdf_bytes.getvalue() + sig_page_bytes

        pdf_result = upload_file(final_bytes, f"pdf_firmado_{alumno_id}_{reglamento_id}.pdf")
        if not pdf_result:
            return {"exito": False, "mensaje": "Error al guardar el PDF firmado."}

        firma.fecha_firma = datetime.now(timezone.utc)
        firma.url_pdf_firmado_cloudinary = pdf_result["secure_url"]
        firma.ip_address = request.client.host if request.client else None
        db.commit()

        audit_log(
            db, None, "FIRMA", "reglamento", firma.id,
            f"Tutor {tutor.nombre} {tutor.apellido_paterno} firmó reglamento {reglamento.titulo} del alumno {alumno.nombrecompleto} {alumno.apellido_paterno}"
        )

        if tutor.email:
            tutor_nombre_local = f"{tutor.nombre} {tutor.apellido_paterno}"
            alumno_nombre_local = f"{alumno.nombrecompleto} {alumno.apellido_paterno}"
            reg_titulo_local = reglamento.titulo
            reg_version_local = reglamento.version
            pdf_url = pdf_result["secure_url"]
            logo_url = settings.LOGO_URL
            fecha_local = datetime.now().strftime('%d/%m/%Y %H:%M')
            email_tutor = tutor.email

            def enviar_confirmacion():
                try:
                    html_confirmacion = f"""
                    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
                        <div style="text-align:center;padding:20px 0;">
                            <img src="{logo_url}" alt="Katira's Gymnastics" style="width:120px;">
                            <h1 style="color:#0d47a1;margin:10px 0 0;">Katira's Gymnastics</h1>
                        </div>
                        <div style="background:#f0fdf4;border-radius:8px;padding:25px;margin:15px 0;border:1px solid #86efac;">
                            <h2 style="color:#166534;margin:0 0 10px;">&#10003; Reglamento firmado exitosamente</h2>
                            <p style="font-size:14px;color:#333;">
                                Hola <strong>{tutor_nombre_local}</strong>,<br><br>
                                Has firmado el reglamento de <strong>{alumno_nombre_local}</strong>
                                ({reg_titulo_local} v{reg_version_local}).<br><br>
                                Fecha de firma: {fecha_local}
                            </p>
                            <p style="font-size:14px;color:#333;margin-top:15px;">
                                Puedes descargar el PDF firmado en el siguiente enlace:<br>
                                <a href="{pdf_url}" style="color:#0d47a1;">{pdf_url}</a>
                            </p>
                        </div>
                        <p style="text-align:center;font-size:11px;color:#aaa;">
                            Katira's Gymnastics &mdash; Este es un mensaje autom&aacute;tico.
                        </p>
                    </div>
                    """
                    enviar_email_html(
                        destinatario_email=email_tutor,
                        asunto=f"Katira's Gymnastics - Reglamento firmado ({alumno_nombre_local})",
                        cuerpo_html=html_confirmacion,
                    )
                except Exception as e:
                    logger.warning("No se pudo enviar confirmacion a %s: %s", email_tutor, e)

            background_tasks.add_task(enviar_confirmacion)

        return {"exito": True, "mensaje": "Reglamento firmado exitosamente."}

    except Exception as e:
        logger.error("Error al procesar firma: %s", e, exc_info=True)
        return {"exito": False, "mensaje": "Error al procesar la firma. Intente de nuevo."}


@router_public.get("/firma", response_class=HTMLResponse)
def pagina_firma(token: str = Query(...), db: Session = Depends(get_db)):
    payload = _decodificar_token(token)
    error_html = ""
    datos_json = "null"
    logo_url = LOGO_URL

    if not payload:
        error_html = "<div class='error-box'>El enlace no es válido o está corrupto.</div>"
    else:
        alumno_id = payload.get("alumno_id")
        reglamento_id = payload.get("reglamento_id")

        alumno = db.query(Alumno).filter(Alumno.id == alumno_id, Alumno.is_deleted == False).first()
        tutor = db.query(Tutor).filter(Tutor.alumno_id == alumno_id).first() if alumno else None
        reglamento = (
            db.query(Reglamento)
            .filter(Reglamento.id == reglamento_id, Reglamento.is_deleted == False)
            .first()
        )
        firma = (
            db.query(FirmaReglamento)
            .filter(FirmaReglamento.token_usado == token, FirmaReglamento.is_deleted == False)
            .first()
        )

        if not all([alumno, tutor, reglamento, firma]):
            error_html = "<div class='error-box'>No se pudieron cargar los datos. El enlace podría no ser válido.</div>"
        else:
            exp = payload.get("exp")
            if isinstance(exp, (int, float)) and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                error_html = "<div class='error-box'>Este enlace ha expirado (vigencia de 30 días). Contacta a la academia para obtener uno nuevo.</div>"
            elif firma.fecha_firma:
                error_html = "<div class='error-box'>Este reglamento ya fue firmado anteriormente. Gracias.</div>"
            else:
                datos_json = json.dumps({
                    "token": token,
                    "alumno": f"{alumno.nombrecompleto} {alumno.apellido_paterno}",
                    "tutor": f"{tutor.nombre} {tutor.apellido_paterno}",
                    "tutorTelefono": tutor.telefono,
                    "tutorEmail": tutor.email,
                    "titulo": reglamento.titulo,
                    "version": reglamento.version,
                    "urlPdf": reglamento.url_pdf_cloudinary,
                })

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Firma de Reglamento - Katira's Gymnastics</title>
<style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'Segoe UI',Arial,sans-serif; background:#f0f2f5; color:#333; min-height:100vh; }}
  .container {{ max-width:800px; margin:0 auto; padding:15px; }}
  .header {{ text-align:center; padding:25px 0 15px; }}
  .header img {{ width:100px; height:auto; }}
  .header h1 {{ font-size:1.3rem; color:#0d47a1; margin-top:5px; }}
  .info-box {{ background:white; border-radius:10px; padding:15px 20px; margin:12px 0; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
  .info-box p {{ margin:4px 0; font-size:14px; }}
  .info-box strong {{ color:#0d47a1; }}
  .error-box {{ background:#fff5f5; border:1px solid #fecaca; border-radius:10px; padding:30px; text-align:center; color:#dc2626; font-size:16px; margin:40px 0; }}
  .pdf-section {{ background:white; border-radius:10px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.06); margin:12px 0; }}
  .pdf-section iframe {{ width:100%; height:500px; border:none; }}
  .pdf-placeholder {{ padding:60px 20px; text-align:center; color:#666; background:#fafafa; }}
  .pdf-placeholder a {{ color:#0d47a1; font-weight:600; }}
  .firma-box {{ background:white; border-radius:10px; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.06); margin:12px 0; }}
  .firma-box h3 {{ font-size:1rem; color:#333; margin-bottom:12px; }}
  #signature-canvas {{ width:100%; height:160px; border:2px dashed #ccc; border-radius:8px; cursor:crosshair; touch-action:none; }}
  .firma-actions {{ display:flex; gap:10px; margin-top:10px; }}
  .firma-actions button {{ flex:1; padding:10px; border:none; border-radius:6px; font-size:14px; cursor:pointer; }}
  .btn-limpiar {{ background:#f5f5f5; color:#666; }}
  .btn-limpiar:hover {{ background:#e5e5e5; }}
  .btn-aceptar {{ padding:14px; width:100%; background:#0d47a1; color:white; border:none; border-radius:8px; font-size:16px; font-weight:600; cursor:pointer; margin-top:12px; }}
  .btn-aceptar:disabled {{ background:#aaa; cursor:not-allowed; }}
  .btn-aceptar:hover:not(:disabled) {{ background:#0a3a8a; }}
  .loading {{ text-align:center; padding:30px; color:#666; }}
  .spinner {{ border:3px solid #e0e0e0; border-top:3px solid #0d47a1; border-radius:50%; width:30px; height:30px; animation:spin 0.8s linear infinite; margin:0 auto 10px; }}
  @keyframes spin {{ to {{ transform:rotate(360deg); }} }}
  .checkbox-box {{ display:flex; align-items:center; gap:8px; margin:10px 0; font-size:14px; }}
  .checkbox-box input[type=checkbox] {{ width:18px; height:18px; cursor:pointer; }}
  .mensaje-exito {{ background:#f0fdf4; border:2px solid #86efac; border-radius:10px; padding:30px; text-align:center; margin:40px 0; }}
  .mensaje-exito h2 {{ color:#166534; font-size:1.3rem; margin-bottom:10px; }}
  .mensaje-exito p {{ color:#333; font-size:14px; }}
  .mensaje-error {{ background:#fef2f2; border:2px solid #fecaca; border-radius:10px; padding:30px; text-align:center; margin:40px 0; }}
  .mensaje-error h2 {{ color:#dc2626; font-size:1.3rem; margin-bottom:10px; }}
  .mensaje-error p {{ color:#333; font-size:14px; }}
  .btn-reintentar {{ display:inline-block; margin-top:15px; padding:10px 24px; background:#dc2626; color:white; border:none; border-radius:6px; font-size:14px; font-weight:600; cursor:pointer; }}
  .btn-reintentar:hover {{ background:#b91c1c; }}
  @media (max-width:600px) {{ .pdf-section iframe {{ height:350px; }} }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <img src="{logo_url}" alt="Katira's Gymnastics">
    <h1>Katira's Gymnastics</h1>
  </div>
  <div id="app">
    <div id="mensaje-error">{error_html}</div>
    <div id="contenido-formulario" style="display:{'none' if error_html else 'block'}">
      <div id="info-alumno" class="info-box"></div>
      <div class="pdf-section">
        <div id="pdf-container" class="pdf-placeholder">
          <p>Cargando documento...</p>
          <div class="spinner"></div>
        </div>
      </div>
      <div class="firma-box">
        <h3>Firma del Tutor</h3>
        <p style="font-size:13px;color:#666;margin-bottom:8px;">Firme aqu&iacute; con su dedo o mouse</p>
        <canvas id="signature-canvas"></canvas>
        <div class="firma-actions">
          <button class="btn-limpiar" onclick="limpiarFirma()">Limpiar</button>
        </div>
        <div class="checkbox-box">
          <input type="checkbox" id="acepto" onchange="actualizarBoton()">
          <label for="acepto">He le&iacute;do y acepto el reglamento interno de la academia</label>
        </div>
        <button class="btn-aceptar" id="btn-firmar" disabled onclick="firmar()">Firmar y Aceptar</button>
        <div id="mensaje-exito" style="display:none;" class="mensaje-exito">
          <img src="{settings.LOGO_URL}" alt="Katira's Gymnastics" style="width:80px;height:auto;margin-bottom:15px;">
          <h2>&#10003; Documento firmado con &eacute;xito</h2>
          <p>El reglamento ha sido firmado correctamente. En breve recibir&aacute; una copia del documento firmado en su correo electr&oacute;nico.</p>
          <p style="margin-top:10px;font-size:13px;color:#666;">Ya puede cerrar esta ventana.</p>
        </div>
        <div id="mensaje-error" style="display:none;" class="mensaje-error">
          <img src="{settings.LOGO_URL}" alt="Katira's Gymnastics" style="width:80px;height:auto;margin-bottom:15px;">
          <h2>&#10008; Error al firmar</h2>
          <p id="error-texto">No se pudo procesar la firma. Intente de nuevo.</p>
          <button class="btn-reintentar" onclick="reintentar()">Volver a intentar</button>
        </div>
      </div>
    </div>
  </div>
</div>
<script>
const datos = {datos_json};
const canvas = document.getElementById('signature-canvas');
const ctx = canvas.getContext('2d');
let dibujando = false;
let firmaVacia = true;

function redimensionarCanvas() {{
  const rect = canvas.parentElement.getBoundingClientRect();
  const w = Math.min(rect.width - 4, 750);
  canvas.width = w;
  canvas.height = 160;
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = '#ccc';
  ctx.lineWidth = 1;
  ctx.strokeRect(0, 0, canvas.width, canvas.height);
  firmaVacia = true;
}}

function getPos(e) {{
  const rect = canvas.getBoundingClientRect();
  const x = (e.touches ? e.touches[0].clientX : e.clientX) - rect.left;
  const y = (e.touches ? e.touches[0].clientY : e.clientY) - rect.top;
  return {{ x, y }};
}}

function empezar(e) {{
  e.preventDefault();
  dibujando = true;
  const p = getPos(e);
  ctx.beginPath();
  ctx.moveTo(p.x, p.y);
}}

function mover(e) {{
  e.preventDefault();
  if (!dibujando) return;
  const p = getPos(e);
  ctx.lineTo(p.x, p.y);
  ctx.strokeStyle = '#1a1a1a';
  ctx.lineWidth = 2.5;
  ctx.lineCap = 'round';
  ctx.stroke();
  firmaVacia = false;
}}

function terminar(e) {{
  e.preventDefault();
  dibujando = false;
  ctx.beginPath();
}}

canvas.addEventListener('mousedown', empezar);
canvas.addEventListener('mousemove', mover);
canvas.addEventListener('mouseup', terminar);
canvas.addEventListener('mouseleave', terminar);
canvas.addEventListener('touchstart', empezar, {{ passive: false }});
canvas.addEventListener('touchmove', mover, {{ passive: false }});
canvas.addEventListener('touchend', terminar, {{ passive: false }});

function limpiarFirma() {{
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = '#ccc';
  ctx.lineWidth = 1;
  ctx.strokeRect(0, 0, canvas.width, canvas.height);
  firmaVacia = true;
  actualizarBoton();
}}

function actualizarBoton() {{
  const acepto = document.getElementById('acepto').checked;
  document.getElementById('btn-firmar').disabled = !(acepto && !firmaVacia);
}}

function firmar() {{
  if (firmaVacia || !document.getElementById('acepto').checked) return;
  const btn = document.getElementById('btn-firmar');
  btn.disabled = true;
  btn.textContent = 'Enviando...';

  const firmaData = canvas.toDataURL('image/png');

  fetch('/api/v1/reglamento/firmar', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ token: datos.token, firma_base64: firmaData }})
  }})
  .then(r => r.json())
  .then(data => {{
    if (data.exito) {{
      document.getElementById('mensaje-exito').style.display = 'block';
      document.querySelector('.firma-box').style.display = 'none';
      document.getElementById('info-alumno').style.display = 'none';
      document.getElementById('pdf-container').style.display = 'none';
    }} else {{
      showError(data.mensaje || 'No se pudo procesar la firma. Intente de nuevo.');
    }}
  }})
  .catch(() => {{
    showError('Error de conexi\u00f3n. Verifique su internet e intente de nuevo.');
  }});
}}

function showError(msg) {{
  document.getElementById('error-texto').textContent = msg;
  document.getElementById('mensaje-error').style.display = 'block';
  document.querySelector('.firma-box').style.display = 'none';
  document.getElementById('info-alumno').style.display = 'none';
  document.getElementById('pdf-container').style.display = 'none';
}}

function reintentar() {{
  document.getElementById('mensaje-error').style.display = 'none';
  document.querySelector('.firma-box').style.display = '';
  document.getElementById('info-alumno').style.display = '';
  document.getElementById('pdf-container').style.display = '';
  redimensionarCanvas();
  document.getElementById('btn-firmar').disabled = true;
  document.getElementById('btn-firmar').textContent = 'Firmar y Aceptar';
}}

function cargarDatos() {{
  if (!datos) return;
  document.getElementById('info-alumno').innerHTML = `
    <p><strong>Tutor:</strong> ${{datos.tutor}} <span style="color:#666;">(${{datos.tutorEmail || 'Sin correo'}})</span></p>
    <p><strong>Alumno(a):</strong> ${{datos.alumno}}</p>
    <p><strong>Documento:</strong> ${{datos.titulo}} (v${{datos.version}})</p>
  `;
  const pdfContainer = document.getElementById('pdf-container');
  if (datos.urlPdf) {{
    pdfContainer.innerHTML = `<iframe src="${{datos.urlPdf}}" title="Reglamento"></iframe>`;
  }} else {{
    pdfContainer.innerHTML = `<div class="pdf-placeholder"><p>No se pudo cargar el documento.</p></div>`;
  }}
  redimensionarCanvas();
}}

window.addEventListener('load', () => {{
  cargarDatos();
  redimensionarCanvas();
}});
window.addEventListener('resize', redimensionarCanvas);
</script>
</body>
</html>""")
