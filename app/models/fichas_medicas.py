from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FichaMedica(Base):
    __tablename__ = "fichas_medicas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    alumno_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("alumnos.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    tipo_sangre: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    alergias: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    medicamentos: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    condiciones_medicas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nss: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    alumno: Mapped["Alumno"] = relationship("Alumno", back_populates="ficha_medica")
