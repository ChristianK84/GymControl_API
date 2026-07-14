import base64
import json
import logging
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings

logger = logging.getLogger(__name__)

OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _obtener_access_token() -> str | None:
    try:
        body = urlencode({
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "refresh_token": settings.GMAIL_REFRESH_TOKEN,
            "grant_type": "refresh_token",
        }).encode()

        req = Request(
            OAUTH_TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            token = data.get("access_token")
            if token:
                return token
            logger.warning("OAuth response sin access_token (status %s)", resp.getcode())
            return None

    except Exception as exc:
        logger.warning("Error al obtener access token OAuth2: %s", exc)
        return None


def enviar_recibo_email(
    destinatario_email: str,
    asunto: str,
    cuerpo_html: str,
    pdf_bytes: bytes,
    pdf_filename: str = "Recibo_Membresia.pdf",
) -> bool:
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_REFRESH_TOKEN or not settings.EMAIL_FROM:
        logger.warning("Gmail OAuth no configurado (GMAIL_CLIENT_ID, GMAIL_REFRESH_TOKEN o EMAIL_FROM vacios)")
        return False

    access_token = _obtener_access_token()
    if not access_token:
        logger.error("No se pudo obtener access token OAuth2")
        return False

    try:
        msg = MIMEMultipart("mixed")
        msg["From"] = formataddr(("GymControl", settings.EMAIL_FROM))
        msg["To"] = destinatario_email
        msg["Subject"] = asunto

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(cuerpo_html, "html"))
        msg.attach(alt)

        adjunto = MIMEBase("application", "octet-stream")
        adjunto.set_payload(pdf_bytes)
        __import__("email").encoders.encode_base64(adjunto)
        adjunto.add_header(
            "Content-Disposition",
            "attachment",
            filename=("utf-8", "", pdf_filename),
        )
        msg.attach(adjunto)

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        body = json.dumps({"raw": raw}).encode()

        req = Request(
            GMAIL_SEND_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urlopen(req, timeout=15) as resp:
            status = resp.getcode()
            if 200 <= status < 300:
                logger.info("Recibo enviado a %s (status %s)", destinatario_email, status)
                return True
            logger.warning("Gmail API respondio %s para %s", status, destinatario_email)
            return False

    except Exception as exc:
        logger.warning("Error al enviar recibo por email a %s: %s", destinatario_email, exc)


def enviar_email_html(
    destinatario_email: str,
    asunto: str,
    cuerpo_html: str,
) -> bool:
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_REFRESH_TOKEN or not settings.EMAIL_FROM:
        logger.warning("Gmail OAuth no configurado")
        return False

    access_token = _obtener_access_token()
    if not access_token:
        logger.error("No se pudo obtener access token OAuth2")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = formataddr(("GymControl", settings.EMAIL_FROM))
        msg["To"] = destinatario_email
        msg["Subject"] = asunto
        msg.attach(MIMEText(cuerpo_html, "html"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        body = json.dumps({"raw": raw}).encode()

        req = Request(
            GMAIL_SEND_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urlopen(req, timeout=15) as resp:
            status = resp.getcode()
            if 200 <= status < 300:
                logger.info("Email enviado a %s (status %s)", destinatario_email, status)
                return True
            logger.warning("Gmail API respondio %s para %s", status, destinatario_email)
            return False

    except Exception as exc:
        logger.warning("Error al enviar email a %s: %s", destinatario_email, exc)
        return False
        return False
