import base64
import json
import logging
from urllib.request import Request, urlopen

from app.core.config import settings

logger = logging.getLogger(__name__)

SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"


def enviar_recibo_email(
    destinatario_email: str,
    asunto: str,
    cuerpo_html: str,
    pdf_bytes: bytes,
    pdf_filename: str = "Recibo_Membresia.pdf",
) -> bool:
    if not settings.SENDGRID_API_KEY or not settings.EMAIL_FROM:
        logger.warning("SendGrid no configurado (SENDGRID_API_KEY o EMAIL_FROM vacios)")
        return False

    try:
        body = json.dumps({
            "personalizations": [{"to": [{"email": destinatario_email}], "subject": asunto}],
            "from": {"email": settings.EMAIL_FROM, "name": "GymControl"},
            "content": [{"type": "text/html", "value": cuerpo_html}],
            "attachments": [{
                "content": base64.b64encode(pdf_bytes).decode(),
                "filename": pdf_filename,
                "type": "application/pdf",
                "disposition": "attachment",
            }],
        }).encode()

        req = Request(
            SENDGRID_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urlopen(req, timeout=15) as resp:
            status = resp.getcode()
            if 200 <= status < 300:
                logger.info("Recibo enviado a %s (status %s)", destinatario_email, status)
                return True
            logger.warning("SendGrid respondio %s para %s", status, destinatario_email)
            return False

    except Exception as exc:
        logger.warning("Error al enviar recibo por email a %s: %s", destinatario_email, exc)
        return False
