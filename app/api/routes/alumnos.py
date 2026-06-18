import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_maestro, get_current_user, require_maestro
from app.core.database import get_db
from app.core.email import enviar_recibo_email
from app.core.qr_utils import generar_qr_png
from app.models import Alumno, ContactoEmergencia, FichaMedica, Maestro, Tutor, User
from app.schemas.alumnos import (
    AlumnoCreate,
    AlumnoResponse,
    AlumnoUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alumnos", tags=["alumnos"])


def _alumno_base_query(db: Session):
    return db.query(Alumno).options(
        joinedload(Alumno.tutor),
        joinedload(Alumno.contacto_emergencia),
        joinedload(Alumno.ficha_medica),
    )


def _autorizar_alumno(alumno_id: int, db: Session, current_maestro: Maestro | None) -> Alumno:
    """Obtiene un alumno activo y verifica que el maestro tenga acceso."""
    alumno = _alumno_base_query(db).filter(
        Alumno.id == alumno_id, Alumno.is_deleted == False
    ).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    if current_maestro and alumno.maestro_id != current_maestro.id:
        raise HTTPException(status_code=403, detail="No autorizado para este alumno")
    return alumno


@router.post("/", response_model=AlumnoResponse, status_code=201)
def create_alumno(
    payload: AlumnoCreate,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    maestro_id = current_maestro.id if current_maestro else payload.maestro_id

    alumno = Alumno(
        nombrecompleto=payload.nombrecompleto,
        apellido_paterno=payload.apellido_paterno,
        apellido_materno=payload.apellido_materno,
        rama=payload.rama,
        fecha_nacimiento=payload.fecha_nacimiento,
        maestro_id=maestro_id,
        fotografia=payload.fotografia,
        fecha_inscripcion=payload.fecha_inscripcion,
    )
    db.add(alumno)
    db.flush()

    db.add(Tutor(**payload.tutor.model_dump(), alumno_id=alumno.id))
    db.add(ContactoEmergencia(**payload.contacto_emergencia.model_dump(), alumno_id=alumno.id))
    db.add(FichaMedica(**payload.ficha_medica.model_dump(), alumno_id=alumno.id))
    db.commit()

    return _alumno_base_query(db).filter(Alumno.id == alumno.id).first()


@router.get("/", response_model=list[AlumnoResponse])
def list_alumnos(
    include_deleted: bool = Query(False),
    maestro_id: int = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    q = _alumno_base_query(db)
    if not include_deleted:
        q = q.filter(Alumno.is_deleted == False)
    if current_maestro:
        q = q.filter(Alumno.maestro_id == current_maestro.id)
    elif maestro_id:
        q = q.filter(Alumno.maestro_id == maestro_id)
    return q.order_by(Alumno.id).all()


@router.get("/cumpleaños", response_model=list[AlumnoResponse])
def list_cumpleanios(
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    today = date.today()
    end_date = today + timedelta(days=30)

    today_mmdd = today.strftime('%m-%d')
    end_mmdd = end_date.strftime('%m-%d')
    bd = func.to_char(Alumno.fecha_nacimiento, 'MM-DD')

    q = _alumno_base_query(db).filter(Alumno.is_deleted == False)

    if current_maestro:
        q = q.filter(Alumno.maestro_id == current_maestro.id)

    if today_mmdd > end_mmdd:
        q = q.filter(or_(bd >= today_mmdd, bd <= end_mmdd))
    else:
        q = q.filter(bd.between(today_mmdd, end_mmdd))

    return q.order_by(bd).all()


@router.get("/{alumno_id}", response_model=AlumnoResponse)
def get_alumno(
    alumno_id: int,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    return _autorizar_alumno(alumno_id, db, current_maestro)


@router.put("/{alumno_id}", response_model=AlumnoResponse)
def update_alumno(
    alumno_id: int,
    payload: AlumnoUpdate,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    alumno = _autorizar_alumno(alumno_id, db, current_maestro)

    update_data = payload.model_dump(exclude_unset=True)

    for field in ("nombrecompleto", "apellido_paterno", "apellido_materno",
                  "rama", "fecha_nacimiento", "fotografia",
                  "fecha_inscripcion", "is_active"):
        if field in update_data:
            setattr(alumno, field, update_data[field])

    if current_maestro:
        update_data.pop("maestro_id", None)
    elif "maestro_id" in update_data:
        alumno.maestro_id = update_data["maestro_id"]

    if payload.tutor is not None:
        if alumno.tutor:
            for k, v in payload.tutor.model_dump(exclude_unset=True).items():
                setattr(alumno.tutor, k, v)
        else:
            db.add(Tutor(**payload.tutor.model_dump(exclude_unset=True), alumno_id=alumno.id))

    if payload.contacto_emergencia is not None:
        if alumno.contacto_emergencia:
            for k, v in payload.contacto_emergencia.model_dump(exclude_unset=True).items():
                setattr(alumno.contacto_emergencia, k, v)
        else:
            db.add(ContactoEmergencia(**payload.contacto_emergencia.model_dump(exclude_unset=True), alumno_id=alumno.id))

    if payload.ficha_medica is not None:
        if alumno.ficha_medica:
            for k, v in payload.ficha_medica.model_dump(exclude_unset=True).items():
                setattr(alumno.ficha_medica, k, v)
        else:
            db.add(FichaMedica(**payload.ficha_medica.model_dump(exclude_unset=True), alumno_id=alumno.id))

    db.commit()
    db.refresh(alumno)
    return alumno


@router.post("/{alumno_id}/enviar-qr")
def enviar_qr_alumno(
    alumno_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    alumno = _autorizar_alumno(alumno_id, db, current_maestro)

    tutor = db.query(Tutor).filter(Tutor.alumno_id == alumno.id).first()
    if not tutor:
        raise HTTPException(status_code=400, detail="El alumno no tiene tutor registrado")
    if not tutor.email:
        raise HTTPException(status_code=400, detail="El tutor no tiene email registrado")

    logger.info("Programando envio de QR de alumno %s a %s", alumno_id, tutor.email)

    def enviar():
        try:
            qr_bytes = generar_qr_png(str(alumno.id))
            html = f"""\
<html><body style="font-family:Arial,sans-serif;color:#333;padding:20px">
<h2 style="color:#007bff;">Katiras Gymnastics</h2>
<p>Estimado(a) <b>{tutor.nombre}</b>,</p>
<p>Adjuntamos el codigo QR de <b>{alumno.nombrecompleto} {alumno.apellido_paterno}</b>.</p>
<p style="padding:12px;background:#f8f9fa;border-radius:8px;text-align:center">
<b>Presente este QR en la entrada del gimnasio</b><br>
para registrar la asistencia de su hijo(a).
</p>
<p>Gracias por su preferencia.</p>
<p style="color:#6c757d;font-size:12px">Katiras Gymnastics - GymControl</p>
</body></html>"""

            ok = enviar_recibo_email(
                destinatario_email=tutor.email,
                asunto=f"Codigo QR - {alumno.nombrecompleto} {alumno.apellido_paterno}",
                cuerpo_html=html,
                pdf_bytes=qr_bytes,
                pdf_filename=f"QR_{alumno.nombrecompleto}.png",
            )
            if ok:
                logger.info("QR enviado exitosamente a %s para alumno %s", tutor.email, alumno_id)
            else:
                logger.error("enviar_recibo_email retorno False para %s", tutor.email)
        except Exception as exc:
            logger.warning("Error al enviar QR del alumno %s: %s", alumno_id, exc)

    background_tasks.add_task(enviar)
    return {"message": f"QR programado para envio a {tutor.email}"}


@router.delete("/{alumno_id}", status_code=204)
def delete_alumno(
    alumno_id: int,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    alumno = db.query(Alumno).filter(Alumno.id == alumno_id, Alumno.is_deleted == False).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    if current_maestro and alumno.maestro_id != current_maestro.id:
        raise HTTPException(status_code=403, detail="No autorizado para este alumno")

    alumno.is_deleted = True
    alumno.is_active = False
    db.commit()
