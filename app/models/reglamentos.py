from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Reglamento(Base):
    __tablename__ = "reglamentos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    url_pdf_cloudinary: Mapped[str] = mapped_column(String(500), nullable=False)
    cloudinary_public_id: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    firmas: Mapped[list["FirmaReglamento"]] = relationship("FirmaReglamento", back_populates="reglamento")


class FirmaReglamento(Base):
    __tablename__ = "firmas_reglamento"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    reglamento_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reglamentos.id", ondelete="RESTRICT"), nullable=False
    )
    alumno_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("alumnos.id", ondelete="CASCADE"), nullable=False
    )
    tutor_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tutores.id", ondelete="CASCADE"), nullable=False
    )
    token_usado: Mapped[str] = mapped_column(String(500), nullable=False)
    url_pdf_firmado_cloudinary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cloudinary_public_id_firmado: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    fecha_firma: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    expira_en: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    reglamento: Mapped[Reglamento] = relationship("Reglamento", back_populates="firmas")
    alumno: Mapped["Alumno"] = relationship("Alumno", back_populates="firmas_reglamento")
    tutor: Mapped["Tutor"] = relationship("Tutor", back_populates="firmas_reglamento")
