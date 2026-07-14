from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReglamentoCreate(BaseModel):
    titulo: str = Field(max_length=200)
    descripcion: Optional[str] = Field(default=None, max_length=1000)
    version: str = Field(max_length=20)
    url_pdf_cloudinary: str = Field(max_length=500)
    cloudinary_public_id: str = Field(max_length=200)


class ReglamentoUpdate(BaseModel):
    titulo: Optional[str] = Field(default=None, max_length=200)
    descripcion: Optional[str] = Field(default=None, max_length=1000)
    version: Optional[str] = Field(default=None, max_length=20)
    is_active: Optional[bool] = None
    url_pdf_cloudinary: Optional[str] = Field(default=None, max_length=500)
    cloudinary_public_id: Optional[str] = Field(default=None, max_length=200)


class ReglamentoResponse(BaseModel):
    id: int
    titulo: str
    descripcion: Optional[str]
    version: str
    url_pdf_cloudinary: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerarLinksPayload(BaseModel):
    reglamento_id: int
    alumno_ids: list[int] = Field(min_length=1)


class GenerarLinksResponse(BaseModel):
    enviados: int
    total: int


class FirmaReglamentoResponse(BaseModel):
    id: int
    reglamento_id: int
    alumno_id: int
    tutor_id: int
    alumno_nombre: Optional[str] = None
    tutor_nombre: Optional[str] = None
    url_pdf_firmado_cloudinary: Optional[str] = None
    fecha_firma: Optional[datetime] = None
    expira_en: datetime
    estado: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FirmarPayload(BaseModel):
    token: str = Field(min_length=10)
    firma_base64: str = Field(min_length=50)


class ValidarTokenResponse(BaseModel):
    valido: bool
    alumno_nombre: Optional[str] = None
    tutor_nombre: Optional[str] = None
    tutor_telefono: Optional[str] = None
    tutor_email: Optional[str] = None
    titulo_reglamento: Optional[str] = None
    version: Optional[str] = None
    url_pdf: Optional[str] = None
    ya_firmado: bool = False
    expirado: bool = False
    mensaje: Optional[str] = None
