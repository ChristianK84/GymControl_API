from datetime import date, datetime, timedelta
from typing import Literal, Optional

import re

from pydantic import BaseModel, Field, field_validator


# ── Tutor ──

_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
_TELEFONO_PATTERN = re.compile(r"^[\d\s\-\(\)\+\.]+$")


class TutorCreate(BaseModel):
    nombre: str = Field(max_length=100)
    apellido_paterno: str = Field(max_length=100)
    apellido_materno: Optional[str] = Field(default=None, max_length=100)
    telefono: str = Field(max_length=20)
    email: str = Field(max_length=150)

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str) -> str:
        v = v.strip()
        if not _TELEFONO_PATTERN.match(v) or len(re.sub(r"\D", "", v)) < 10:
            raise ValueError("Teléfono inválido (mínimo 10 dígitos)")
        return v

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        if not _EMAIL_PATTERN.match(v):
            raise ValueError("Formato de email invalido")
        return v


class TutorUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not _TELEFONO_PATTERN.match(v) or len(re.sub(r"\D", "", v)) < 10:
                raise ValueError("Teléfono inválido (mínimo 10 dígitos)")
        return v

    @field_validator("email")
    @classmethod
    def validar_email(cls, v: str) -> str:
        if v is not None and not _EMAIL_PATTERN.match(v):
            raise ValueError("Formato de email invalido")
        return v


class TutorResponse(BaseModel):
    id: int
    alumno_id: int
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str]
    telefono: str
    email: str

    model_config = {"from_attributes": True}


# ── Contacto de emergencia ──

class ContactoEmergenciaCreate(BaseModel):
    nombre: str = Field(max_length=100)
    apellido_paterno: str = Field(max_length=100)
    apellido_materno: Optional[str] = Field(default=None, max_length=100)
    telefono: str = Field(max_length=20)

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: str) -> str:
        v = v.strip()
        if not _TELEFONO_PATTERN.match(v) or len(re.sub(r"\D", "", v)) < 10:
            raise ValueError("Teléfono inválido (mínimo 10 dígitos)")
        return v


class ContactoEmergenciaUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    telefono: Optional[str] = None

    @field_validator("telefono")
    @classmethod
    def validar_telefono(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not _TELEFONO_PATTERN.match(v) or len(re.sub(r"\D", "", v)) < 10:
                raise ValueError("Teléfono inválido (mínimo 10 dígitos)")
        return v


class ContactoEmergenciaResponse(BaseModel):
    id: int
    alumno_id: int
    nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str]
    telefono: str

    model_config = {"from_attributes": True}


# ── Ficha médica ──

class FichaMedicaCreate(BaseModel):
    tipo_sangre: Optional[Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]] = Field(default=None, max_length=10)
    alergias: Optional[str] = Field(default=None, max_length=500)
    medicamentos: Optional[str] = Field(default=None, max_length=500)
    condiciones_medicas: Optional[str] = Field(default=None, max_length=500)
    nss: Optional[str] = Field(default=None, max_length=50)


class FichaMedicaUpdate(BaseModel):
    tipo_sangre: Optional[str] = None
    alergias: Optional[str] = None
    medicamentos: Optional[str] = None
    condiciones_medicas: Optional[str] = None
    nss: Optional[str] = None


class FichaMedicaResponse(BaseModel):
    id: int
    alumno_id: int
    tipo_sangre: Optional[str]
    alergias: Optional[str]
    medicamentos: Optional[str]
    condiciones_medicas: Optional[str]
    nss: Optional[str]

    model_config = {"from_attributes": True}


# ── Alumno ──

class AlumnoCreate(BaseModel):
    nombrecompleto: str = Field(max_length=150)
    apellido_paterno: str = Field(max_length=100)
    apellido_materno: Optional[str] = Field(default=None, max_length=100)
    rama: Literal["Varonil", "Femenil"]
    fecha_nacimiento: date
    maestro_id: int = Field(gt=0)
    fotografia: Optional[str] = Field(default=None, max_length=500)
    fecha_inscripcion: date
    tutor: TutorCreate
    contacto_emergencia: ContactoEmergenciaCreate
    ficha_medica: FichaMedicaCreate

    @field_validator("fecha_nacimiento")
    @classmethod
    def validar_fecha_nacimiento(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        if v.year < 1900:
            raise ValueError("La fecha de nacimiento es inválida")
        return v

    @field_validator("fecha_inscripcion")
    @classmethod
    def validar_fecha_inscripcion(cls, v: date) -> date:
        if v > date.today() + timedelta(days=1):
            raise ValueError("La fecha de inscripción no puede ser futura")
        return v


class AlumnoUpdate(BaseModel):
    nombrecompleto: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    rama: Optional[str] = None
    fecha_nacimiento: Optional[date] = None
    maestro_id: Optional[int] = None
    fotografia: Optional[str] = None
    fecha_inscripcion: Optional[date] = None
    is_active: Optional[bool] = None
    tutor: Optional[TutorUpdate] = None
    contacto_emergencia: Optional[ContactoEmergenciaUpdate] = None
    ficha_medica: Optional[FichaMedicaUpdate] = None


class MembresiaResumen(BaseModel):
    is_active: bool
    fecha_vencimiento: date
    esta_vencida: bool = False
    pagado: bool = True
    estado: str | None = None


class AlumnoResponse(BaseModel):
    id: int
    nombrecompleto: str
    apellido_paterno: str
    apellido_materno: Optional[str]
    rama: str
    fecha_nacimiento: date
    maestro_id: int
    fotografia: Optional[str]
    fecha_inscripcion: date
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    tutor: Optional[TutorResponse]
    contacto_emergencia: Optional[ContactoEmergenciaResponse]
    ficha_medica: Optional[FichaMedicaResponse]
    inscripcion: Optional[MembresiaResumen] = None
    membresia: Optional[MembresiaResumen] = None

    model_config = {"from_attributes": True}
