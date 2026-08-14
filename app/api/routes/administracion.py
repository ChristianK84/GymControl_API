import secrets
import logging

import requests as http_requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.email import enviar_recibo_email
from app.core.security import hash_password
from app.models import Maestro, User
from app.schemas.administracion import (
    BienvenidaPayload,
    BienvenidaResultado,
    FallidoItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/administracion", tags=["administracion"])

PDF_URL = "https://res.cloudinary.com/dyvqspnz7/image/upload/v1786748045/Gu%C3%ADa_de_Usuario_GymControl_Maestro_oagq9q.pdf"

APP_LINK = "https://drive.google.com/file/d/14DiXGB3z10AuzWuAd7QghdfZ37dTfs4s/view?usp=sharing"


def _build_welcome_email(
    nombre_completo: str,
    username: str,
    password: str,
) -> str:
    return f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <div style="text-align:center;padding:20px 0;">
            <img src="https://res.cloudinary.com/dyvqspnz7/image/upload/v1786748045/Logo.jpg" alt="Katira's Gymnastics" style="width:120px;">
            <h1 style="color:#0d47a1;margin:10px 0 0;">Katira's Gymnastics</h1>
        </div>
        <div style="background:#f5f5f5;border-radius:8px;padding:25px;margin:15px 0;">
            <p style="font-size:16px;color:#333;">Hola <strong>{nombre_completo}</strong>,</p>
            <p style="font-size:14px;color:#555;">
                ¡Bienvenido a <strong>GymControl</strong>! Adjuntamos la guía de uso del sistema.
            </p>
            <div style="text-align:center;margin:20px 0;">
                <a href="{APP_LINK}" style="display:inline-block;background:#0d47a1;color:white;padding:12px 28px;border-radius:6px;text-decoration:none;font-weight:600;">
                    Descargar App
                </a>
            </div>
            <p style="font-size:14px;color:#555;margin-bottom:5px;"><strong>Tus credenciales:</strong></p>
            <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
                <tr>
                    <td style="padding:8px 12px;background:#e2e8f0;font-weight:600;width:40%;border:1px solid #cbd5e1;">Usuario</td>
                    <td style="padding:8px 12px;border:1px solid #cbd5e1;"><code>{username}</code></td>
                </tr>
                <tr>
                    <td style="padding:8px 12px;background:#e2e8f0;font-weight:600;border:1px solid #cbd5e1;">Contraseña</td>
                    <td style="padding:8px 12px;border:1px solid #cbd5e1;"><code>{password}</code></td>
                </tr>
            </table>
            <p style="font-size:12px;color:#999;text-align:center;">
                Este email contiene tu contraseña temporal. Cámbiala después de iniciar sesión.
            </p>
        </div>
        <p style="text-align:center;font-size:11px;color:#aaa;">
            Katira's Gymnastics &mdash; Este es un mensaje autom&aacute;tico.
        </p>
    </div>
    """


@router.post("/enviar-bienvenida", response_model=BienvenidaResultado)
def enviar_bienvenida(
    payload: BienvenidaPayload,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    fallidos: list[FallidoItem] = []
    enviados = 0

    # Descargar PDF una sola vez
    try:
        logger.info("Descargando PDF manual desde Cloudinary...")
        pdf_response = http_requests.get(PDF_URL, timeout=30)
        pdf_response.raise_for_status()
        pdf_bytes = pdf_response.content
        logger.info("PDF descargado OK: %d bytes", len(pdf_bytes))
    except Exception as exc:
        logger.error("Error al descargar PDF de bienvenida: %s", exc)
        raise HTTPException(status_code=500, detail="Error al descargar el manual de usuario")

    # Obtener token una sola vez
    from app.core.email import _obtener_access_token
    access_token = _obtener_access_token()
    if not access_token:
        raise HTTPException(status_code=500, detail="Error al obtener token de correo")

    for mid in payload.maestro_ids:
        maestro = (
            db.query(Maestro)
            .filter(Maestro.id == mid, Maestro.is_deleted == False)
            .first()
        )
        if not maestro:
            fallidos.append(FallidoItem(id=mid, nombre="(desconocido)", error="Maestro no encontrado"))
            continue
        if not maestro.email:
            fallidos.append(FallidoItem(id=mid, nombre=f"{maestro.nombre} {maestro.apellido_paterno}", error="Sin email registrado"))
            continue
        if not maestro.user_id:
            fallidos.append(FallidoItem(id=mid, nombre=f"{maestro.nombre} {maestro.apellido_paterno}", error="Sin usuario asociado"))
            continue

        user = db.query(User).filter(User.id == maestro.user_id, User.is_deleted == False).first()
        if not user:
            fallidos.append(FallidoItem(id=mid, nombre=f"{maestro.nombre} {maestro.apellido_paterno}", error="Usuario no encontrado"))
            continue

        # Generar password nuevo y resetear
        new_password = secrets.token_urlsafe(8)
        user.password_hash = hash_password(new_password)
        user.token_version += 1
        db.commit()

        # Construir email
        nombre_completo = f"{maestro.nombre} {maestro.apellido_paterno}"
        html = _build_welcome_email(nombre_completo, user.username, new_password)

        # Enviar
        logger.info("Enviando email a maestro id=%d, email=%s", maestro.id, maestro.email)
        ok = enviar_recibo_email(
            destinatario_email=maestro.email,
            asunto="Bienvenido a GymControl - Katira's Gymnastics",
            cuerpo_html=html,
            pdf_bytes=pdf_bytes,
            pdf_filename="Guia_GymControl_Maestro.pdf",
            access_token=access_token,
        )

        if ok:
            logger.info("Email enviado OK a %s", maestro.email)
            enviados += 1
            audit_log(db, _admin.id, "SEND_EMAIL", "maestro", maestro.id,
                      f"Bienvenida enviada a {maestro.email}")
        else:
            logger.error("FALLÓ envío a maestro id=%d, email=%s", maestro.id, maestro.email)
            fallidos.append(FallidoItem(id=mid, nombre=nombre_completo, error=f"Falló el envío a {maestro.email}"))

    return BienvenidaResultado(enviados=enviados, fallidos=fallidos)
