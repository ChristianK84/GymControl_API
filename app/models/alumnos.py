from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Alumno(Base):
    __tablename__ = "alumnos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nombrecompleto: Mapped[str] = mapped_column(String(150), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido_materno: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rama: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_nacimiento: Mapped[date] = mapped_column(Date, nullable=False)
    maestro_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("maestros.id", ondelete="RESTRICT"), nullable=False
    )
    fotografia: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
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

    maestro: Mapped["Maestro"] = relationship("Maestro", back_populates="alumnos")
    membresias: Mapped[list["Membresia"]] = relationship("Membresia", back_populates="alumno")
    asistencias: Mapped[list["Asistencia"]] = relationship("Asistencia", back_populates="alumno")
    tutor: Mapped[Optional["Tutor"]] = relationship("Tutor", back_populates="alumno", uselist=False)
    contacto_emergencia: Mapped[Optional["ContactoEmergencia"]] = relationship(
        "ContactoEmergencia", back_populates="alumno", uselist=False
    )
    ficha_medica: Mapped[Optional["FichaMedica"]] = relationship(
        "FichaMedica", back_populates="alumno", uselist=False
    )
