import logging
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from app.core.config import settings

logger = logging.getLogger(__name__)


def enviar_recibo_email(
    destinatario_email: str,
    asunto: str,
    cuerpo_html: str,
    pdf_bytes: bytes,
    pdf_filename: str = "Recibo_Membresia.pdf",
) -> bool:
    try:
        msg = MIMEMultipart("mixed")
        msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_USER))
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

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        logger.info("Recibo enviado a %s", destinatario_email)
        return True
    except Exception as exc:
        logger.warning("Error al enviar recibo por email a %s: %s", destinatario_email, exc)
        return False
