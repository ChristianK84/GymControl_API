from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Inscripcion(Base):
    __tablename__ = "inscripciones"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alumno_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("alumnos.id", ondelete="CASCADE"), nullable=False
    )
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    porcentaje_beca: Mapped[int] = mapped_column(Integer, default=0)
    monto_final: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    anio: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_pago: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date] = mapped_column(Date, nullable=False)
    pagado: Mapped[bool] = mapped_column(Boolean, default=True)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    alumno: Mapped["Alumno"] = relationship("Alumno", back_populates="inscripciones")
    registrador: Mapped[Optional["User"]] = relationship("User")
