"""
Seed de los 5 tipos de membresia definidos con el cliente.
Ejecutar: python scripts/seed_tipos_membresia.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal
from app.models import TipoMembresia

TIPOS = [
    {
        "nombre": "Lunes a Viernes — Básico — Mensual",
        "descripcion": "2 días a la semana, 3 horas por clase",
        "costo_base": 1000,
        "duracion_dias": 30,
        "dias_incluidos": "lunes-viernes",
        "dias_por_semana": 2,
        "horas_por_clase": 3,
        "nivel_competitivo": False,
        "color": "#3b82f6",
    },
    {
        "nombre": "Lunes a Jueves — Competitivo — Mensual",
        "descripcion": "4 días a la semana, 3 horas por clase. Nivel competitivo.",
        "costo_base": 1500,
        "duracion_dias": 30,
        "dias_incluidos": "lunes-jueves",
        "dias_por_semana": 4,
        "horas_por_clase": 3,
        "nivel_competitivo": True,
        "color": "#ef4444",
    },
    {
        "nombre": "Sábado — General — Mensual",
        "descripcion": "Solo sábados, 3 horas de entrenamiento",
        "costo_base": 650,
        "duracion_dias": 30,
        "dias_incluidos": "sabado",
        "dias_por_semana": 1,
        "horas_por_clase": 3,
        "nivel_competitivo": False,
        "color": "#f59e0b",
    },
    {
        "nombre": "Lunes a Viernes — Bebés — Mensual",
        "descripcion": "2 días a la semana, 2 horas por clase",
        "costo_base": 850,
        "duracion_dias": 30,
        "dias_incluidos": "lunes-viernes",
        "dias_por_semana": 2,
        "horas_por_clase": 2,
        "nivel_competitivo": False,
        "color": "#10b981",
    },
    {
        "nombre": "Libre — Completo — Anual",
        "descripcion": "Acceso libre todos los días, pago anual",
        "costo_base": 1000,
        "duracion_dias": 365,
        "dias_incluidos": "libre",
        "dias_por_semana": None,
        "horas_por_clase": None,
        "nivel_competitivo": False,
        "color": "#8b5cf6",
    },
]


def seed():
    db = SessionLocal()
    try:
        for data in TIPOS:
            nombre = data["nombre"]
            existente = db.query(TipoMembresia).filter(TipoMembresia.nombre == nombre).first()
            if existente:
                for key, value in data.items():
                    setattr(existente, key, value)
                print(f"[UPD] {nombre}")
            else:
                db.add(TipoMembresia(**data))
                print(f"[NEW] {nombre}")
        db.commit()
        print("\nSeed completado.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
