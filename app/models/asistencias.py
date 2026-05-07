from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Asistencia(Base):
    __tablename__ = "asistencias"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alumno_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("alumnos.id", ondelete="CASCADE"), nullable=False
    )
    maestro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("maestros.id"), nullable=False
    )
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    asistio: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registrado_por: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (
        UniqueConstraint("alumno_id", "fecha", name="uq_asistencia_diaria"),
    )

    alumno: Mapped["Alumno"] = relationship("Alumno", back_populates="asistencias")
    maestro: Mapped["Maestro"] = relationship("Maestro")
    registrador: Mapped[Optional["User"]] = relationship("User")
