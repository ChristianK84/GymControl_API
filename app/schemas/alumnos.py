from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Tutor ──

class TutorCreate(BaseModel):
    nombre: str = Field(max_length=100)
    apellido_paterno: str = Field(max_length=100)
    apellido_materno: Optional[str] = None
    telefono: str = Field(max_length=20)
    email: str = Field(max_length=150)


class TutorUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None


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
    apellido_materno: Optional[str] = None
    telefono: str = Field(max_length=20)


class ContactoEmergenciaUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido_paterno: Optional[str] = None
    apellido_materno: Optional[str] = None
    telefono: Optional[str] = None


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
    tipo_sangre: Optional[str] = None
    alergias: Optional[str] = None
    medicamentos: Optional[str] = None
    condiciones_medicas: Optional[str] = None
    nss: Optional[str] = None


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
    apellido_materno: Optional[str] = None
    rama: str = Field(max_length=20)
    fecha_nacimiento: date
    maestro_id: int
    fotografia: Optional[str] = None
    fecha_inscripcion: date
    tutor: TutorCreate
    contacto_emergencia: ContactoEmergenciaCreate
    ficha_medica: FichaMedicaCreate


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

    model_config = {"from_attributes": True}
