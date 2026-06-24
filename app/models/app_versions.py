from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppVersion(Base):
    __tablename__ = "app_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    version_code: Mapped[int] = mapped_column(Integer, nullable=False)
    bundle_url: Mapped[str] = mapped_column(String(500), nullable=False)
    release_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
