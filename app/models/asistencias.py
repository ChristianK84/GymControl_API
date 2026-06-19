from datetime import datetime
from typing import Optional

from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Asistencia(Base):
    __tablename__ = "asistencias"

    __table_args__ = (
        UniqueConstraint("alumno_id", "fecha", name="uq_asistencia_diaria"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alumno_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("alumnos.id", ondelete="CASCADE"), nullable=False
    )
    maestro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("maestros.id", ondelete="RESTRICT"), nullable=False
    )
    fecha: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    asistio: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    es_dia_extra: Mapped[bool] = mapped_column(Boolean, default=False)
    costo_extra: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    alumno: Mapped["Alumno"] = relationship("Alumno", back_populates="asistencias")
    maestro: Mapped["Maestro"] = relationship("Maestro")
    registrador: Mapped[Optional["User"]] = relationship("User")
