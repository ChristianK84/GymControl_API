import logging
from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_maestro, get_current_user, require_maestro
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.email import enviar_recibo_email
from app.core.pdf import generar_recibo_membresia
from app.models import Alumno, Maestro, Membresia, TipoMembresia, Transaccion, Tutor, User
from app.schemas.membresias import (
    MembresiaCreate,
    MembresiaResponse,
    MembresiaUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/membresias", tags=["membresias"])

# IDs de estados
ACTIVA = 1
VENCIDA = 2
CANCELADA = 3


def _membresia_base_query(db: Session):
    return db.query(Membresia).options(
        joinedload(Membresia.alumno),
        joinedload(Membresia.tipo_membresia),
        joinedload(Membresia.estado),
    )


def _actualizar_estados_vencidos(db: Session):
    """Actualiza a Vencida las membresias cuya fecha ya paso y aun estan Activa."""
    hoy = date.today()
    vencidas = db.query(Membresia).filter(
        Membresia.fecha_vencimiento < hoy,
        Membresia.estado_id == ACTIVA,
    ).all()
    for m in vencidas:
        m.estado_id = VENCIDA
    if vencidas:
        db.commit()


@router.post("/", response_model=MembresiaResponse, status_code=201)
def create_membresia(
    payload: MembresiaCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
    current_user: User = Depends(get_current_user),
):
    alumno = db.query(Alumno).filter(
        Alumno.id == payload.alumno_id, Alumno.is_deleted == False
    ).first()
    if not alumno:
        raise HTTPException(status_code=400, detail="Alumno no encontrado o inactivo")
    if current_maestro and alumno.maestro_id != current_maestro.id:
        raise HTTPException(status_code=403, detail="No autorizado para este alumno")

    tipo = db.query(TipoMembresia).filter(
        TipoMembresia.id == payload.tipo_membresia_id, TipoMembresia.is_deleted == False
    ).first()
    if not tipo:
        raise HTTPException(status_code=400, detail="Tipo de membresia no encontrado")

    membresia = Membresia(
        alumno_id=payload.alumno_id,
        tipo_membresia_id=payload.tipo_membresia_id,
        costo_real=payload.costo_real,
        porcentaje_beca=payload.porcentaje_beca,
        fecha_inicio=payload.fecha_inicio,
        fecha_vencimiento=payload.fecha_vencimiento,
        estado_id=ACTIVA,
        pagado=payload.pagado,
        notas=payload.notas,
    )
    db.add(membresia)
    db.flush()

    transaccion = Transaccion(
        tipo_transaccion=1,
        categoria="Membresia",
        subcategoria=tipo.nombre,
        descripcion=f"Membresia {tipo.nombre} - {alumno.nombrecompleto} {alumno.apellido_paterno}",
        monto=payload.costo_real,
        fecha=date.today(),
        membresia_id=membresia.id,
        alumno_id=alumno.id,
        registrado_por=current_user.id,
    )
    db.add(transaccion)
    db.commit()

    audit_log(db, current_user.id, "CREATE", "membresia", membresia.id,
              f"{current_user.username} creó membresía {tipo.nombre} para alumno #{alumno.id}")

    tutor = db.query(Tutor).filter(Tutor.alumno_id == alumno.id).first()

    if not tutor:
        logger.info("Alumno %s no tiene tutor registrado, se omite envio de recibo", alumno.id)
    elif not tutor.email:
        logger.info("Tutor de alumno %s no tiene email, se omite envio de recibo", alumno.id)
    else:
        logger.info("Programando envio de recibo de membresia %s a %s", membresia.id, tutor.email)

        maestro_nombre = ""
        if alumno.maestro_id:
            maestro_obj = db.query(Maestro).filter(Maestro.id == alumno.maestro_id).first()
            if maestro_obj:
                maestro_nombre = f"{maestro_obj.nombre} {maestro_obj.apellido_paterno}"

        def enviar():
            try:
                logger.info("Generando PDF para membresia %s...", membresia.id)
                pdf_bytes = generar_recibo_membresia(
                    alumno_nombre=f"{alumno.nombrecompleto} {alumno.apellido_paterno} {alumno.apellido_materno or ''}".strip(),
                    alumno_rama=alumno.rama,
                    tutor_nombre=f"{tutor.nombre} {tutor.apellido_paterno} {tutor.apellido_materno or ''}".strip(),
                    tutor_telefono=tutor.telefono,
                    tutor_email=tutor.email,
                    membresia_id=membresia.id,
                    tipo_nombre=tipo.nombre,
                    costo_real=float(payload.costo_real),
                    porcentaje_beca=payload.porcentaje_beca,
                    fecha_inicio=payload.fecha_inicio.isoformat(),
                    fecha_vencimiento=payload.fecha_vencimiento.isoformat(),
                    pagado=payload.pagado,
                    maestro_nombre=maestro_nombre,
                    fecha_emision=datetime.now().strftime("%d/%m/%Y"),
                )
                logger.info("PDF generado: %s bytes para membresia %s", len(pdf_bytes), membresia.id)

                html = f"""\
<html><body style="font-family:Arial,sans-serif;color:#333;padding:20px">
<h2 style="color:#007bff;">Katiras Gymnastics</h2>
<p>Estimado(a) <b>{tutor.nombre}</b>,</p>
<p>Adjuntamos el recibo de membresia de <b>{alumno.nombrecompleto} {alumno.apellido_paterno}</b>.</p>
<table style="border-collapse:collapse;margin:12px 0">
<tr><td style="padding:4px 12px;font-weight:bold">Tipo:</td><td>{tipo.nombre}</td></tr>
<tr><td style="padding:4px 12px;font-weight:bold">Monto:</td><td>${float(payload.costo_real):,.2f} MXN</td></tr>
<tr><td style="padding:4px 12px;font-weight:bold">Vigencia:</td><td>{payload.fecha_inicio} al {payload.fecha_vencimiento}</td></tr>
</table>
<p>Gracias por su preferencia.</p>
<p style="color:#6c757d;font-size:12px">Katiras Gymnastics - GymControl</p>
</body></html>"""

                ok = enviar_recibo_email(
                    destinatario_email=tutor.email,
                    asunto=f"Recibo de Membresia - {alumno.nombrecompleto} {alumno.apellido_paterno}",
                    cuerpo_html=html,
                    pdf_bytes=pdf_bytes,
                    pdf_filename=f"Recibo_Membresia_{membresia.id}.pdf",
                )
                if ok:
                    logger.info("Email enviado exitosamente a %s para membresia %s", tutor.email, membresia.id)
                else:
                    logger.error("enviar_recibo_email retorno False para %s", tutor.email)
            except Exception as exc:
                logger.warning("Error en envio de recibo para membresia %s: %s", membresia.id, exc)

        background_tasks.add_task(enviar)

    return _membresia_base_query(db).filter(Membresia.id == membresia.id).first()


@router.get("/", response_model=list[MembresiaResponse])
def list_membresias(
    alumno_id: int = Query(None),
    estado_id: int = Query(None),
    pagado: bool = Query(None),
    vencidas: bool = Query(False),
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    _actualizar_estados_vencidos(db)

    q = _membresia_base_query(db)
    if current_maestro:
        q = q.join(Alumno, Membresia.alumno_id == Alumno.id).filter(Alumno.maestro_id == current_maestro.id)
    if alumno_id:
        q = q.filter(Membresia.alumno_id == alumno_id)
    if estado_id:
        q = q.filter(Membresia.estado_id == estado_id)
    if vencidas:
        q = q.filter(Membresia.estado_id == VENCIDA)
    if pagado is not None:
        q = q.filter(Membresia.pagado == pagado)
    return q.order_by(Membresia.fecha_vencimiento.desc()).all()


@router.get("/impagas", response_model=list[MembresiaResponse])
def list_membresias_impagas(
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    _actualizar_estados_vencidos(db)

    q = (
        _membresia_base_query(db)
        .filter(
            Membresia.estado_id == ACTIVA,
            Membresia.pagado == False,
        )
    )
    if current_maestro:
        q = q.join(Alumno, Membresia.alumno_id == Alumno.id).filter(Alumno.maestro_id == current_maestro.id)
    return q.order_by(Membresia.fecha_vencimiento.asc()).all()


def _autorizar_membresia(membresia_id: int, db: Session, current_maestro: Maestro | None):
    """Obtiene una membresia y verifica que el maestro tenga acceso al alumno."""
    membresia = _membresia_base_query(db).filter(Membresia.id == membresia_id).first()
    if not membresia:
        raise HTTPException(status_code=404, detail="Membresia no encontrada")
    if current_maestro:
        alumno = db.query(Alumno).filter(Alumno.id == membresia.alumno_id).first()
        if not alumno or alumno.maestro_id != current_maestro.id:
            raise HTTPException(status_code=403, detail="No autorizado para esta membresia")
    return membresia


@router.get("/{membresia_id}", response_model=MembresiaResponse)
def get_membresia(
    membresia_id: int,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    _actualizar_estados_vencidos(db)
    return _autorizar_membresia(membresia_id, db, current_maestro)


@router.put("/{membresia_id}", response_model=MembresiaResponse)
def update_membresia(
    membresia_id: int,
    payload: MembresiaUpdate,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    membresia = _autorizar_membresia(membresia_id, db, current_maestro)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(membresia, field, value)

    db.commit()
    db.refresh(membresia)

    audit_log(db, _maestro.id, "UPDATE", "membresia", membresia.id,
              f"{_maestro.username} actualizó membresía #{membresia_id}")

    return membresia


@router.post("/{membresia_id}/enviar-recibo")
def reenviar_recibo(
    membresia_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
    current_user: User = Depends(get_current_user),
):
    membresia = _autorizar_membresia(membresia_id, db, current_maestro)

    alumno = db.query(Alumno).filter(Alumno.id == membresia.alumno_id).first()
    tutor = db.query(Tutor).filter(Tutor.alumno_id == alumno.id).first()

    if not tutor:
        raise HTTPException(status_code=400, detail="El alumno no tiene tutor registrado")
    if not tutor.email:
        raise HTTPException(status_code=400, detail="El tutor no tiene email registrado")

    tipo = db.query(TipoMembresia).filter(TipoMembresia.id == membresia.tipo_membresia_id).first()

    maestro_nombre = ""
    if alumno.maestro_id:
        maestro_obj = db.query(Maestro).filter(Maestro.id == alumno.maestro_id).first()
        if maestro_obj:
            maestro_nombre = f"{maestro_obj.nombre} {maestro_obj.apellido_paterno}"

    logger.info("Programando reenvio de recibo de membresia %s a %s", membresia_id, tutor.email)

    def enviar():
        try:
            logger.info("Generando PDF para membresia %s...", membresia_id)
            pdf_bytes = generar_recibo_membresia(
                alumno_nombre=f"{alumno.nombrecompleto} {alumno.apellido_paterno} {alumno.apellido_materno or ''}".strip(),
                alumno_rama=alumno.rama,
                tutor_nombre=f"{tutor.nombre} {tutor.apellido_paterno} {tutor.apellido_materno or ''}".strip(),
                tutor_telefono=tutor.telefono,
                tutor_email=tutor.email,
                membresia_id=membresia.id,
                tipo_nombre=tipo.nombre,
                costo_real=float(membresia.costo_real),
                porcentaje_beca=membresia.porcentaje_beca,
                fecha_inicio=membresia.fecha_inicio.isoformat(),
                fecha_vencimiento=membresia.fecha_vencimiento.isoformat(),
                pagado=membresia.pagado,
                maestro_nombre=maestro_nombre,
                fecha_emision=datetime.now().strftime("%d/%m/%Y"),
            )
            logger.info("PDF generado: %s bytes para membresia %s", len(pdf_bytes), membresia_id)

            html = f"""\
<html><body style="font-family:Arial,sans-serif;color:#333;padding:20px">
<h2 style="color:#007bff;">Katiras Gymnastics</h2>
<p>Estimado(a) <b>{tutor.nombre}</b>,</p>
<p>Adjuntamos el recibo de membresia de <b>{alumno.nombrecompleto} {alumno.apellido_paterno}</b>.</p>
<table style="border-collapse:collapse;margin:12px 0">
<tr><td style="padding:4px 12px;font-weight:bold">Tipo:</td><td>{tipo.nombre}</td></tr>
<tr><td style="padding:4px 12px;font-weight:bold">Monto:</td><td>${float(membresia.costo_real):,.2f} MXN</td></tr>
<tr><td style="padding:4px 12px;font-weight:bold">Vigencia:</td><td>{membresia.fecha_inicio} al {membresia.fecha_vencimiento}</td></tr>
</table>
<p>Gracias por su preferencia.</p>
<p style="color:#6c757d;font-size:12px">Katiras Gymnastics - GymControl</p>
</body></html>"""

            ok = enviar_recibo_email(
                destinatario_email=tutor.email,
                asunto=f"Recibo de Membresia - {alumno.nombrecompleto} {alumno.apellido_paterno}",
                cuerpo_html=html,
                pdf_bytes=pdf_bytes,
                pdf_filename=f"Recibo_Membresia_{membresia.id}.pdf",
            )
            if ok:
                logger.info("Reenvio exitoso a %s para membresia %s", tutor.email, membresia_id)
            else:
                logger.error("enviar_recibo_email retorno False para %s", tutor.email)
        except Exception as exc:
            logger.warning("Error en reenvio de recibo para membresia %s: %s", membresia_id, exc)

    background_tasks.add_task(enviar)

    audit_log(db, current_user.id, "SEND_EMAIL", "membresia", membresia_id,
              f"{current_user.username} reenvió recibo de membresía #{membresia_id} a {tutor.email}")

    return {"message": f"Recibo programado para envio a {tutor.email}"}


@router.delete("/{membresia_id}", status_code=204)
def cancelar_membresia(
    membresia_id: int,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    membresia = _autorizar_membresia(membresia_id, db, current_maestro)

    membresia.estado_id = CANCELADA
    db.commit()

    audit_log(db, _maestro.id, "DELETE", "membresia", membresia.id,
              f"{_maestro.username} canceló membresía #{membresia_id}")
