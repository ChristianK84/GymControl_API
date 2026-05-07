from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Alumno(Base):
    __tablename__ = "alumnos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido_materno: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fecha_nacimiento: Mapped[date] = mapped_column(Date, nullable=False)
    genero_id: Mapped[Optional[int]] = mapped_column(
        SmallInteger, ForeignKey("generos.id"), nullable=True
    )
    grupo_edad_id: Mapped[int] = mapped_column(
        SmallInteger, ForeignKey("grupos_edad.id"), nullable=False
    )
    foto: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    nombre_tutor: Mapped[str] = mapped_column(String(150), nullable=False)
    telefono_tutor: Mapped[str] = mapped_column(String(20), nullable=False)
    tipo_sangre: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    alergias: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notas_medicas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    maestro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("maestros.id", ondelete="RESTRICT"), nullable=False
    )
    fecha_inscripcion: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    genero: Mapped[Optional["Genero"]] = relationship("Genero")
    grupo_edad: Mapped["GrupoEdad"] = relationship("GrupoEdad")
    maestro: Mapped["Maestro"] = relationship("Maestro", back_populates="alumnos")
    membresias: Mapped[list["Membresia"]] = relationship("Membresia", back_populates="alumno")
    asistencias: Mapped[list["Asistencia"]] = relationship("Asistencia", back_populates="alumno")
