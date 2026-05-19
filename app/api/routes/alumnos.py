from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Alumno, ContactoEmergencia, FichaMedica, Tutor
from app.schemas.alumnos import (
    AlumnoCreate,
    AlumnoResponse,
    AlumnoUpdate,
)

router = APIRouter(prefix="/alumnos", tags=["alumnos"])


def _alumno_base_query(db: Session):
    return db.query(Alumno).options(
        joinedload(Alumno.tutor),
        joinedload(Alumno.contacto_emergencia),
        joinedload(Alumno.ficha_medica),
    )


@router.post("/", response_model=AlumnoResponse, status_code=201)
def create_alumno(payload: AlumnoCreate, db: Session = Depends(get_db)):
    alumno = Alumno(
        nombrecompleto=payload.nombrecompleto,
        apellido_paterno=payload.apellido_paterno,
        apellido_materno=payload.apellido_materno,
        rama=payload.rama,
        fecha_nacimiento=payload.fecha_nacimiento,
        maestro_id=payload.maestro_id,
        fotografia=payload.fotografia,
        fecha_inscripcion=payload.fecha_inscripcion,
    )
    db.add(alumno)
    db.flush()

    db.add(Tutor(**payload.tutor.model_dump(), alumno_id=alumno.id))
    db.add(ContactoEmergencia(**payload.contacto_emergencia.model_dump(), alumno_id=alumno.id))
    db.add(FichaMedica(**payload.ficha_medica.model_dump(), alumno_id=alumno.id))
    db.commit()

    return _alumno_base_query(db).filter(Alumno.id == alumno.id).first()


@router.get("/", response_model=list[AlumnoResponse])
def list_alumnos(
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = _alumno_base_query(db)
    if not include_deleted:
        q = q.filter(Alumno.is_deleted == False)
    return q.order_by(Alumno.id).all()


@router.get("/{alumno_id}", response_model=AlumnoResponse)
def get_alumno(alumno_id: int, db: Session = Depends(get_db)):
    alumno = _alumno_base_query(db).filter(Alumno.id == alumno_id).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")
    return alumno


@router.put("/{alumno_id}", response_model=AlumnoResponse)
def update_alumno(alumno_id: int, payload: AlumnoUpdate, db: Session = Depends(get_db)):
    alumno = _alumno_base_query(db).filter(Alumno.id == alumno_id).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    update_data = payload.model_dump(exclude_unset=True)

    # Actualizar campos directos del alumno
    for field in ("nombrecompleto", "apellido_paterno", "apellido_materno",
                  "rama", "fecha_nacimiento", "maestro_id", "fotografia",
                  "fecha_inscripcion", "is_active"):
        if field in update_data:
            setattr(alumno, field, update_data[field])

    # Upsert tutor
    if payload.tutor is not None:
        if alumno.tutor:
            for k, v in payload.tutor.model_dump(exclude_unset=True).items():
                setattr(alumno.tutor, k, v)
        else:
            db.add(Tutor(**payload.tutor.model_dump(), alumno_id=alumno.id))

    # Upsert contacto_emergencia
    if payload.contacto_emergencia is not None:
        if alumno.contacto_emergencia:
            for k, v in payload.contacto_emergencia.model_dump(exclude_unset=True).items():
                setattr(alumno.contacto_emergencia, k, v)
        else:
            db.add(ContactoEmergencia(**payload.contacto_emergencia.model_dump(), alumno_id=alumno.id))

    # Upsert ficha_medica
    if payload.ficha_medica is not None:
        if alumno.ficha_medica:
            for k, v in payload.ficha_medica.model_dump(exclude_unset=True).items():
                setattr(alumno.ficha_medica, k, v)
        else:
            db.add(FichaMedica(**payload.ficha_medica.model_dump(), alumno_id=alumno.id))

    db.commit()
    db.refresh(alumno)
    return alumno


@router.delete("/{alumno_id}", status_code=204)
def delete_alumno(alumno_id: int, db: Session = Depends(get_db)):
    alumno = db.query(Alumno).filter(Alumno.id == alumno_id).first()
    if not alumno:
        raise HTTPException(status_code=404, detail="Alumno no encontrado")

    alumno.is_deleted = True
    alumno.is_active = False
    db.commit()
