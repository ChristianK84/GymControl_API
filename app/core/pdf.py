import logging
import os
from io import BytesIO
from urllib.request import urlopen

from fpdf import FPDF

from app.core.config import settings

logger = logging.getLogger(__name__)

_FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
_DEJAVU_REGULAR = os.path.join(_FONTS_DIR, "DejaVuSans.ttf")
_DEJAVU_BOLD = os.path.join(_FONTS_DIR, "DejaVuSans-Bold.ttf")
_FONTS_READY = os.path.isfile(_DEJAVU_REGULAR) and os.path.isfile(_DEJAVU_BOLD)

_logo_bytes: bytes | None = None


def _get_logo_bytes() -> BytesIO:
    global _logo_bytes
    if _logo_bytes is None:
        with urlopen(settings.LOGO_URL, timeout=10) as resp:
            _logo_bytes = resp.read()
    return BytesIO(_logo_bytes)


def generar_recibo_membresia(
    alumno_nombre: str,
    alumno_rama: str,
    tutor_nombre: str,
    tutor_telefono: str,
    tutor_email: str,
    membresia_id: int,
    tipo_nombre: str,
    costo_real: float,
    porcentaje_beca: int,
    fecha_inicio: str,
    fecha_vencimiento: str,
    pagado: bool,
    maestro_nombre: str,
    fecha_emision: str,
) -> bytes:
    pdf = FPDF()
    pdf.add_page()

    fnt = "DejaVu"
    if _FONTS_READY:
        pdf.add_font(fnt, "", _DEJAVU_REGULAR)
        pdf.add_font(fnt, "B", _DEJAVU_BOLD)
    else:
        fnt = "Helvetica"
        logger.warning("Fuentes DejaVu no encontradas, usando Helvetica")

    pdf.set_font(fnt, "B", 18)
    pdf.set_text_color(33, 37, 41)

    try:
        logo = _get_logo_bytes()
        pdf.image(logo, x=10, y=10, w=30)
        pdf.set_xy(45, 14)
    except Exception:
        pdf.set_xy(10, 14)

    pdf.cell(0, 12, "Katiras Gymnastics", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fnt, "", 9)
    pdf.set_text_color(108, 117, 125)
    pdf.cell(0, 5, "Sistema de Gestion Deportiva", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(12)

    pdf.set_draw_color(0, 123, 255)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    pdf.set_font(fnt, "B", 14)
    pdf.set_text_color(0, 123, 255)
    pdf.cell(0, 10, "RECIBO DE MEMBRESIA", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(fnt, "", 10)
    pdf.set_text_color(33, 37, 41)
    pdf.cell(0, 6, f"Folio #{membresia_id}", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)

    costo_final = costo_real * (1 - porcentaje_beca / 100)

    def seccion(titulo: str):
        pdf.set_font(fnt, "B", 11)
        pdf.set_text_color(0, 123, 255)
        pdf.cell(0, 8, titulo, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(33, 37, 41)

    def fila(label: str, valor: str):
        pdf.set_font(fnt, "", 10)
        pdf.cell(60, 7, label, align="R")
        pdf.set_font(fnt, "B", 10)
        pdf.cell(0, 7, f"  {valor}", new_x="LMARGIN", new_y="NEXT")

    seccion("ALUMNO")
    fila("Nombre:", alumno_nombre)
    fila("Rama:", alumno_rama)
    fila("Maestro:", maestro_nombre)

    pdf.ln(4)
    seccion("TUTOR")
    fila("Nombre:", tutor_nombre)
    fila("Telefono:", tutor_telefono)
    fila("Email:", tutor_email)

    pdf.ln(4)
    seccion("DETALLE DE MEMBRESIA")

    col1 = 95
    col2 = 95
    x_start = 10

    pdf.set_font(fnt, "B", 9)
    pdf.set_fill_color(0, 123, 255)
    pdf.set_text_color(255, 255, 255)
    pdf.set_x(x_start)
    pdf.cell(col1, 7, "  Concepto", border=1, fill=True)
    pdf.cell(col2, 7, "Detalle  ", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    def detalle_fila(concepto: str, detalle: str):
        pdf.set_font(fnt, "", 9)
        pdf.set_text_color(33, 37, 41)
        pdf.set_x(x_start)
        pdf.cell(col1, 7, f"  {concepto}", border=1)
        pdf.set_font(fnt, "B", 9)
        pdf.cell(col2, 7, f"{detalle}  ", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    detalle_fila("Tipo", tipo_nombre)
    detalle_fila("Costo", f"${costo_real:,.2f} MXN")
    detalle_fila("Beca", f"{porcentaje_beca}%")
    detalle_fila("Costo Final", f"${costo_final:,.2f} MXN")
    detalle_fila("Inicio", fecha_inicio)
    detalle_fila("Vencimiento", fecha_vencimiento)
    detalle_fila("Pagado", "Si" if pagado else "No")

    pdf.ln(12)
    pdf.set_draw_color(0, 123, 255)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)

    pdf.set_font(fnt, "", 8)
    pdf.set_text_color(108, 117, 125)
    pdf.cell(0, 5, f"Emitido: {fecha_emision}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Katiras Gymnastics - Sistema GymControl", align="C", new_x="LMARGIN", new_y="NEXT")

    return pdf.output()
