from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Transaccion(Base):
    __tablename__ = "transacciones"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tipo_transaccion: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategoria: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    membresia_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("membresias.id"), nullable=True
    )
    alumno_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("alumnos.id"), nullable=True
    )
    registrado_por: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    membresia: Mapped[Optional["Membresia"]] = relationship("Membresia")
    alumno: Mapped[Optional["Alumno"]] = relationship("Alumno")
    registrador: Mapped[Optional["User"]] = relationship("User")
