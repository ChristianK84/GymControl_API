from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models import Alumno, Asistencia, Maestro, Transaccion
from app.schemas.reportes import AsistenciasPorMaestroResponse, MaestroAsistencias

router = APIRouter(prefix="/reportes", tags=["reportes"])


def _decimal(val) -> Decimal:
    return Decimal(str(val or 0))


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _admin=Depends(require_admin)):
    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    # Total alumnos activos
    total_alumnos = db.scalar(
        select(func.count(Alumno.id)).filter(
            Alumno.is_deleted == False, Alumno.is_active == True
        )
    ) or 0

    # Ingreso mensual (tipo_transaccion=1 = ingreso)
    ingreso_mensual = db.scalar(
        select(func.coalesce(func.sum(Transaccion.monto), 0)).filter(
            Transaccion.tipo_transaccion == 1,
            Transaccion.is_deleted == False,
            Transaccion.fecha >= inicio_mes,
        )
    )

    # Asistencia hoy (% de alumnos activos que asistieron hoy)
    asistentes_hoy = db.scalar(
        select(func.count(func.distinct(Asistencia.alumno_id))).filter(
            Asistencia.is_deleted == False,
            Asistencia.fecha >= hoy,
            Asistencia.fecha < hoy + timedelta(days=1),
        )
    ) or 0
    tasa_asistencia = round(asistentes_hoy / total_alumnos * 100, 1) if total_alumnos > 0 else 0

    # Ausentismo prolongado: alumnos activos sin asistencia en 14 días
    ausentismo = db.scalar(
        select(func.count(Alumno.id)).filter(
            Alumno.is_deleted == False,
            Alumno.is_active == True,
            ~Alumno.id.in_(
                select(Asistencia.alumno_id).filter(
                    Asistencia.is_deleted == False,
                    Asistencia.fecha >= hoy - timedelta(days=14),
                )
            ),
        )
    ) or 0

    # Asistencia semanal (últimas 5 semanas)
    desde = hoy - timedelta(weeks=5, days=hoy.weekday())
    filas = db.execute(
        select(
            func.to_char(Asistencia.fecha, "YYYY-MM-DD").label("semana_inicio"),
            func.count(Asistencia.id).label("total"),
        ).filter(
            Asistencia.is_deleted == False,
            Asistencia.fecha >= desde,
        ).group_by(
            func.to_char(Asistencia.fecha, "YYYY-MM-DD"),
        ).order_by(func.min(Asistencia.fecha))
    ).all()

    # Agrupar por semana (ISO week)
    asistencia_semanal = {}
    for f in filas:
        f_inicio = datetime.strptime(f.semana_inicio, "%Y-%m-%d").date()
        lunes = f_inicio - timedelta(days=f_inicio.weekday())
        key = lunes.isoformat()
        asistencia_semanal[key] = asistencia_semanal.get(key, 0) + f.total

    semanas = sorted(asistencia_semanal.keys())[-5:]
    asistencia_semanal_lista = [
        {"semana": f"Sem {i+1}", "valor": min(asistencia_semanal[s], 100)}
        for i, s in enumerate(semanas)
    ]

    return {
        "total_alumnos_activos": _decimal(total_alumnos),
        "ingreso_mensual": _decimal(ingreso_mensual) if ingreso_mensual is not None else Decimal("0"),
        "tasa_asistencia_promedio": Decimal(str(tasa_asistencia)),
        "ausentismo_prolongado": _decimal(ausentismo),
        "asistencia_semanal": asistencia_semanal_lista,
    }


def _generar_semanas_iso(fecha_inicio: date, fecha_fin: date) -> list[dict]:
    """Genera la lista de semanas ISO (lunes-domingo) dentro del rango."""
    # Primer lunes >= fecha_inicio
    primer_lunes = fecha_inicio - timedelta(days=fecha_inicio.weekday())
    if primer_lunes < fecha_inicio:
        primer_lunes += timedelta(days=7)

    semanas = []
    cursor = primer_lunes
    while cursor <= fecha_fin:
        domingo = cursor + timedelta(days=6)
        semanas.append(
            {
                "semana_iso": f"{cursor.isocalendar()[0]}-W{cursor.isocalendar()[1]:02d}",
                "fecha_inicio": cursor,
                "fecha_fin": domingo,
            }
        )
        cursor += timedelta(days=7)
    return semanas


@router.get("/asistencias-por-maestro", response_model=AsistenciasPorMaestroResponse)
def reporte_asistencias_por_maestro(
    fecha_inicio: date | None = Query(None, description="Inicio del rango (default: 8 semanas atrás)"),
    fecha_fin: date | None = Query(None, description="Fin del rango (default: hoy)"),
    maestro_id: int | None = Query(None, description="Filtrar por maestro"),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    """Retorna el conteo de asistencias por maestro y semana ISO (Lun-Dom)."""
    hoy = date.today()
    fecha_fin = fecha_fin or hoy
    fecha_inicio = fecha_inicio or (hoy - timedelta(weeks=8))

    if fecha_inicio > fecha_fin:
        fecha_inicio, fecha_fin = fecha_fin, fecha_inicio

    semanas = _generar_semanas_iso(fecha_inicio, fecha_fin)
    if not semanas:
        return AsistenciasPorMaestroResponse(
            fecha_inicio_global=fecha_inicio,
            fecha_fin_global=fecha_fin,
            semanas=[],
            maestros=[],
        )

    primer_lunes = semanas[0]["fecha_inicio"]
    ultimo_domingo = semanas[-1]["fecha_fin"]

    # Contar asistencias agrupadas por maestro y semana ISO
    query = (
        select(
            Asistencia.maestro_id,
            func.date_trunc("week", Asistencia.fecha).label("semana"),
            func.count().label("total"),
        )
        .join(Maestro, Maestro.id == Asistencia.maestro_id)
        .join(Alumno, Alumno.id == Asistencia.alumno_id)
        .filter(
            Maestro.is_deleted == False,
            Maestro.is_active == True,
            Alumno.is_deleted == False,
            Asistencia.is_deleted == False,
            Asistencia.asistio == True,
            Asistencia.fecha >= primer_lunes,
            Asistencia.fecha < ultimo_domingo + timedelta(days=1),
        )
    )
    if maestro_id:
        query = query.filter(Asistencia.maestro_id == maestro_id)

    query = query.group_by(
        Asistencia.maestro_id,
        func.date_trunc("week", Asistencia.fecha),
    )
    filas = db.execute(query).all()

    # Mapa: (maestro_id, lunes_iso) -> total
    conteo: dict[tuple[int, str], int] = {}
    for f in filas:
        lunes = f.semana
        if isinstance(lunes, datetime):
            lunes = lunes.date()
        conteo[(f.maestro_id, lunes.isoformat())] = f.total

    # Obtener datos de maestros
    maestros_query = db.execute(
        select(Maestro.id, Maestro.nombre, Maestro.apellido_paterno).filter(
            Maestro.is_deleted == False, Maestro.is_active == True
        )
    ).all()
    if maestro_id:
        maestros_query = [m for m in maestros_query if m.id == maestro_id]

    # Construir respuesta: 1 entrada por maestro con dict semana_iso -> total (0 si no hay)
    semanas_labels = [s["semana_iso"] for s in semanas]
    maestros_lista = []
    for m in maestros_query:
        semana_map: dict[str, int] = {}
        total_general = 0
        for s in semanas:
            key = (m.id, s["fecha_inicio"].isoformat())
            val = conteo.get(key, 0)
            semana_map[s["semana_iso"]] = val
            total_general += val
        maestros_lista.append(
            MaestroAsistencias(
                maestro_id=m.id,
                maestro_nombre=m.nombre,
                maestro_apellido_paterno=m.apellido_paterno,
                total_general=total_general,
                semanas=semana_map,
            )
        )

    return AsistenciasPorMaestroResponse(
        fecha_inicio_global=primer_lunes,
        fecha_fin_global=ultimo_domingo,
        semanas=semanas_labels,
        maestros=maestros_lista,
    )
