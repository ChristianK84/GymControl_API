from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import get_current_maestro, require_maestro
from app.core.audit import audit_log
from app.core.database import get_db
from app.models import Alumno, Asistencia, Maestro, Membresia, TipoMembresia
from app.schemas.asistencias import (
    AsistenciaCreate,
    AsistenciaResponse,
    AsistenciaScanRequest,
    AsistenciaScanResponse,
    AsistenciaUpdate,
)

router = APIRouter(prefix="/asistencias", tags=["asistencias"])

ACTIVA = 1
PENDIENTE = 4

_DIA_MAP = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6,
}


def _parsear_dias(dias_incluidos: str) -> set[int]:
    normalizado = dias_incluidos.strip().lower()
    if normalizado == "libre":
        return set(range(7))
    partes = normalizado.split("-")
    if len(partes) == 2 and partes[0] in _DIA_MAP and partes[1] in _DIA_MAP:
        inicio, fin = _DIA_MAP[partes[0]], _DIA_MAP[partes[1]]
        if inicio <= fin:
            return set(range(inicio, fin + 1))
        return set(range(inicio, 7)) | set(range(0, fin + 1))
    dias = {_DIA_MAP.get(d.strip()) for d in normalizado.split(",")}
    dias.discard(None)
    return dias


def _validar_dia_permitido(fecha: date, dias_incluidos: str) -> bool:
    dias_permitidos = _parsear_dias(dias_incluidos)
    return fecha.weekday() in dias_permitidos


def _asistencia_base_query(db: Session):
    return db.query(Asistencia).options(
        joinedload(Asistencia.alumno),
        joinedload(Asistencia.maestro),
    )


def _membresia_activa(alumno_id: int, db: Session) -> Optional[Membresia]:
    return (
        db.query(Membresia)
        .options(joinedload(Membresia.tipo_membresia))
        .filter(
            Membresia.alumno_id == alumno_id,
            Membresia.estado_id.in_([ACTIVA, PENDIENTE]),
        )
        .order_by(Membresia.estado_id)
        .first()
    )


def _validar_visita_extra(alumno_id: int, fecha: date, db: Session) -> Optional[Decimal]:
    membresia = _membresia_activa(alumno_id, db)
    if not membresia or not membresia.tipo_membresia:
        raise HTTPException(status_code=400, detail="El alumno no tiene una membresia activa")

    tipo = membresia.tipo_membresia
    if _validar_dia_permitido(fecha, tipo.dias_incluidos):
        return None

    if not tipo.permite_dias_extra or tipo.costo_dia_extra is None:
        raise HTTPException(
            status_code=403,
            detail=f"Este dia no esta incluido en la membresia '{tipo.nombre}' ({tipo.dias_incluidos})",
        )

    return tipo.costo_dia_extra


def _validar_bloqueo_impago(alumno_id: int, db: Session) -> None:
    membresia = _membresia_activa(alumno_id, db)
    if not membresia or not membresia.tipo_membresia:
        return

    if membresia.pagado:
        return

    if membresia.tipo_membresia.bloquear_impago:
        raise HTTPException(
            status_code=402,
            detail=f"Membresia '{membresia.tipo_membresia.nombre}' pendiente de pago. Asistencia bloqueada.",
        )


def _enriquecer_impago(asistencia, db: Session):
    membresia = _membresia_activa(asistencia.alumno_id, db)
    if membresia and not membresia.pagado and membresia.tipo_membresia:
        asistencia.alerta_impago = (
            f"Atencion: membresia '{membresia.tipo_membresia.nombre}' pendiente de pago (${membresia.costo_real})"
        )
    else:
        asistencia.alerta_impago = None
    return asistencia


_DIA_NOMBRES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


@router.post("/scan", response_model=AsistenciaScanResponse)
def scan_asistencia(payload: AsistenciaScanRequest, db: Session = Depends(get_db), current_user=Depends(require_maestro)):
    alumno = db.query(Alumno).filter(
        Alumno.id == payload.alumno_id, Alumno.is_deleted == False, Alumno.is_active == True
    ).first()
    if not alumno:
        return AsistenciaScanResponse(
            permitido=False, motivo="alumno_inactivo",
            mensaje="Alumno no encontrado o inactivo.",
        )

    if current_user.role_id == 2:
        maestro = db.query(Maestro).filter(
            Maestro.user_id == current_user.id,
            Maestro.is_deleted == False,
            Maestro.is_active == True,
        ).first()
        if not maestro:
            return AsistenciaScanResponse(
                permitido=False, motivo="maestro_invalido",
                mensaje="Tu cuenta de usuario no esta vinculada a ningun maestro.",
            )
        if payload.maestro_id != maestro.id:
            return AsistenciaScanResponse(
                permitido=False, motivo="maestro_no_autorizado",
                mensaje="No puedes registrar asistencia como otro maestro.",
            )

    if alumno.maestro_id != payload.maestro_id:
        return AsistenciaScanResponse(
            permitido=False, motivo="alumno_no_asignado",
            mensaje="Este alumno no esta asignado al maestro seleccionado.",
        )

    membresia = _membresia_activa(payload.alumno_id, db)
    if not membresia or not membresia.tipo_membresia:
        return AsistenciaScanResponse(
            permitido=False, motivo="sin_membresia",
            mensaje="El alumno no tiene una membresía activa o pendiente.",
        )

    tipo = membresia.tipo_membresia
    hoy = date.today()
    dia_nombre = _DIA_NOMBRES[hoy.weekday()]

    dia_permitido = _validar_dia_permitido(hoy, tipo.dias_incluidos)

    if not dia_permitido:
        costo = tipo.costo_dia_extra if tipo.costo_dia_extra is not None else Decimal("0")
        return AsistenciaScanResponse(
            permitido=True, motivo="fuera_de_plan",
            mensaje=f"Hoy ({dia_nombre}) no está incluido en el plan '{tipo.nombre}' "
                    f"({tipo.dias_incluidos})." +
                    (f" Costo extra: ${costo:,.2f}." if costo > 0 else ""),
            costo_extra=costo if costo > 0 else None,
        )

    if not membresia.pagado:
        if tipo.bloquear_impago:
            return AsistenciaScanResponse(
                permitido=False, motivo="impago_bloqueado",
                mensaje=f"Acceso denegado. La membresía '{tipo.nombre}' tiene un pago pendiente de "
                        f"${membresia.costo_real:,.2f}.",
            )
        impago = True
    else:
        impago = False

    now = datetime.now()
    existing = db.query(Asistencia).filter(
        Asistencia.alumno_id == payload.alumno_id,
        Asistencia.fecha >= now.replace(hour=0, minute=0, second=0, microsecond=0),
    ).first()

    if existing:
        return AsistenciaScanResponse(
            permitido=False, motivo="duplicado",
            mensaje="Este alumno ya registró asistencia hoy.",
        )

    asistencia = Asistencia(
        alumno_id=payload.alumno_id,
        maestro_id=payload.maestro_id,
        fecha=now,
        asistio=True,
        es_dia_extra=False,
        costo_extra=Decimal("0"),
        registrado_por=current_user.id,
    )
    if impago:
        asistencia.notas = f"Asistencia registrada con alerta de impago: membresía '{tipo.nombre}' pendiente."

    db.add(asistencia)
    db.commit()

    audit_log(db, current_user.id, "SCAN", "asistencia", asistencia.id,
              f"{current_user.username} registró asistencia de alumno #{alumno.id}")

    result = _asistencia_base_query(db).filter(Asistencia.id == asistencia.id).first()
    result = _enriquecer_impago(result, db)

    if impago:
        return AsistenciaScanResponse(
            permitido=True, motivo="impago_alerta",
            mensaje=f"Membresía '{tipo.nombre}' pendiente de pago (${membresia.costo_real:,.2f}). "
                    f"Asistencia registrada con alerta.",
            asistencia=result,
        )

    return AsistenciaScanResponse(
        permitido=True, motivo="ok",
        mensaje=f"Asistencia registrada — {alumno.nombrecompleto} {alumno.apellido_paterno}.",
        asistencia=result,
    )


@router.post("/", response_model=AsistenciaResponse, status_code=201)
def create_asistencia(
    payload: AsistenciaCreate,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    maestro_id = current_maestro.id if current_maestro else payload.maestro_id

    alumno = db.query(Alumno).filter(
        Alumno.id == payload.alumno_id, Alumno.is_deleted == False
    ).first()
    if not alumno:
        raise HTTPException(status_code=400, detail="Alumno no encontrado o inactivo")
    if current_maestro and alumno.maestro_id != current_maestro.id:
        raise HTTPException(status_code=403, detail="No autorizado para este alumno")

    existing = db.query(Asistencia).filter(
        Asistencia.alumno_id == payload.alumno_id,
        Asistencia.fecha == payload.fecha,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe registro para este alumno en esta fecha")

    fecha_date = payload.fecha.date() if isinstance(payload.fecha, datetime) else payload.fecha

    _validar_bloqueo_impago(payload.alumno_id, db)

    costo_extra = _validar_visita_extra(payload.alumno_id, fecha_date, db)

    es_dia_extra = costo_extra is not None
    costo_final = costo_extra or Decimal("0")

    data = payload.model_dump()
    data["maestro_id"] = maestro_id
    data["registrado_por"] = _maestro.id
    asistencia = Asistencia(**data)
    asistencia.es_dia_extra = es_dia_extra
    asistencia.costo_extra = costo_final
    db.add(asistencia)
    db.commit()

    audit_log(db, _maestro.id, "CREATE", "asistencia", asistencia.id,
              f"{_maestro.username} registró asistencia manual de alumno #{payload.alumno_id}")

    return _enriquecer_impago(
        _asistencia_base_query(db).filter(Asistencia.id == asistencia.id).first(), db
    )


@router.get("/", response_model=list[AsistenciaResponse])
def list_asistencias(
    alumno_id: int = Query(None),
    maestro_id: int = Query(None),
    fecha_desde: datetime = Query(None),
    fecha_hasta: datetime = Query(None),
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    q = _asistencia_base_query(db)
    if alumno_id:
        q = q.filter(Asistencia.alumno_id == alumno_id)
    if current_maestro:
        q = q.filter(Asistencia.maestro_id == current_maestro.id)
    elif maestro_id:
        q = q.filter(Asistencia.maestro_id == maestro_id)
    if fecha_desde:
        q = q.filter(Asistencia.fecha >= fecha_desde)
    if fecha_hasta:
        q = q.filter(Asistencia.fecha <= fecha_hasta)
    results = q.order_by(Asistencia.fecha.desc(), Asistencia.id).all()
    for a in results:
        _enriquecer_impago(a, db)
    return results


@router.get("/{asistencia_id}", response_model=AsistenciaResponse)
def get_asistencia(
    asistencia_id: int,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    asistencia = _asistencia_base_query(db).filter(Asistencia.id == asistencia_id).first()
    if not asistencia:
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")
    if current_maestro and asistencia.maestro_id != current_maestro.id:
        raise HTTPException(status_code=403, detail="No autorizado para esta asistencia")
    return _enriquecer_impago(asistencia, db)


@router.put("/{asistencia_id}", response_model=AsistenciaResponse)
def update_asistencia(
    asistencia_id: int,
    payload: AsistenciaUpdate,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    asistencia = _asistencia_base_query(db).filter(Asistencia.id == asistencia_id).first()
    if not asistencia:
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")
    if current_maestro and asistencia.maestro_id != current_maestro.id:
        raise HTTPException(status_code=403, detail="No autorizado para esta asistencia")

    update_data = payload.model_dump(exclude_unset=True)
    if current_maestro:
        update_data.pop("maestro_id", None)
    for field, value in update_data.items():
        setattr(asistencia, field, value)

    db.commit()
    db.refresh(asistencia)

    audit_log(db, _maestro.id, "UPDATE", "asistencia", asistencia.id,
              f"{_maestro.username} actualizó asistencia #{asistencia_id}")

    return _enriquecer_impago(asistencia, db)


@router.delete("/{asistencia_id}", status_code=204)
def delete_asistencia(
    asistencia_id: int,
    db: Session = Depends(get_db),
    _maestro=Depends(require_maestro),
    current_maestro: Maestro | None = Depends(get_current_maestro),
):
    asistencia = db.query(Asistencia).filter(Asistencia.id == asistencia_id).first()
    if not asistencia:
        raise HTTPException(status_code=404, detail="Asistencia no encontrada")
    if current_maestro and asistencia.maestro_id != current_maestro.id:
        raise HTTPException(status_code=403, detail="No autorizado para esta asistencia")

    db.delete(asistencia)
    db.commit()

    audit_log(db, _maestro.id, "DELETE", "asistencia", asistencia_id,
              f"{_maestro.username} eliminó asistencia #{asistencia_id}")
