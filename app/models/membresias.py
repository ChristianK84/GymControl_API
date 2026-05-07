from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TipoMembresia(Base):
    __tablename__ = "tipos_membresia"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    costo_base: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    duracion_dias: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    membresias: Mapped[list["Membresia"]] = relationship("Membresia", back_populates="tipo_membresia")


class Membresia(Base):
    __tablename__ = "membresias"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alumno_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("alumnos.id", ondelete="CASCADE"), nullable=False
    )
    tipo_membresia_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tipos_membresia.id"), nullable=False
    )
    costo_real: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    estado_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("estados_membresia.id"), nullable=False, default=1
    )
    notas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    alumno: Mapped["Alumno"] = relationship("Alumno", back_populates="membresias")
    tipo_membresia: Mapped["TipoMembresia"] = relationship(
        "TipoMembresia", back_populates="membresias"
    )
    estado: Mapped["EstadoMembresia"] = relationship("EstadoMembresia")
