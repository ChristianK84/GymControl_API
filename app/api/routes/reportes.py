from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.database import get_db
from app.models import Alumno, Asistencia, Transaccion

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
