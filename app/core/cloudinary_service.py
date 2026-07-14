import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

CLOUDINARY_UPLOAD_URL = "https://api.cloudinary.com/v1_1/dyvqspnz7/auto/upload"
UPLOAD_PRESET = "gymcontrol/PDF"


def upload_file(file_bytes: bytes, filename: str = "document.pdf") -> Optional[dict]:
    try:
        res = requests.post(
            CLOUDINARY_UPLOAD_URL,
            files={"file": (filename, file_bytes, "application/pdf")},
            data={"upload_preset": UPLOAD_PRESET},
            timeout=30,
        )
        if res.ok:
            data = res.json()
            logger.info("Archivo subido a Cloudinary: %s", data.get("secure_url"))
            return data
        logger.error("Cloudinary error %s: %s", res.status_code, res.text)
        return None
    except Exception as e:
        logger.error("Error al subir a Cloudinary: %s", e)
        return None
