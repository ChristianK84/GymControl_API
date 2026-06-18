import io

import qrcode


def generar_qr_png(dato: str, size: int = 300) -> bytes:
    img = qrcode.make(dato)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
