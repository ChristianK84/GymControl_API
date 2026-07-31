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
        "descripcion": "2 dias a la semana (lunes a viernes), 3 horas por clase. Limite de 2 visitas por semana.",
        "costo_base": 1100,
        "duracion_dias": 30,
        "dias_incluidos": "lunes-viernes",
        "limite_dias_semana": 2,
        "dias_por_semana": 2,
        "horas_por_clase": 3,
        "nivel_competitivo": False,
        "color": "#3b82f6",
        "permite_dias_extra": True,
        "costo_dia_extra": 150,
        "costo_dia_extra_sabado": 200,
    },
    {
        "nombre": "Lunes a Jueves — Competitivo — Mensual",
        "descripcion": "4 dias a la semana (lunes a jueves), 3 horas por clase. Nivel competitivo.",
        "costo_base": 1500,
        "duracion_dias": 30,
        "dias_incluidos": "lunes-jueves",
        "limite_dias_semana": None,
        "dias_por_semana": 4,
        "horas_por_clase": 3,
        "nivel_competitivo": True,
        "color": "#ef4444",
        "permite_dias_extra": True,
        "costo_dia_extra": 150,
        "costo_dia_extra_sabado": 200,
    },
    {
        "nombre": "Sábado — General — Mensual",
        "descripcion": "Solo sabados, 3 horas de entrenamiento.",
        "costo_base": 750,
        "duracion_dias": 30,
        "dias_incluidos": "sabado",
        "limite_dias_semana": 1,
        "dias_por_semana": 1,
        "horas_por_clase": 3,
        "nivel_competitivo": False,
        "color": "#f59e0b",
        "permite_dias_extra": True,
        "costo_dia_extra": 150,
        "costo_dia_extra_sabado": None,
    },
    {
        "nombre": "Lunes a Viernes — Bebés — Mensual",
        "descripcion": "2 dias a la semana (lunes a viernes), 2 horas por clase.",
        "costo_base": 950,
        "duracion_dias": 30,
        "dias_incluidos": "lunes-viernes",
        "limite_dias_semana": 2,
        "dias_por_semana": 2,
        "horas_por_clase": 2,
        "nivel_competitivo": False,
        "color": "#10b981",
        "permite_dias_extra": True,
        "costo_dia_extra": 150,
        "costo_dia_extra_sabado": 200,
    },
    {
        "nombre": "Libre — Completo — Anual",
        "descripcion": "Cuota de registro anual. No incluye asistencia.",
        "costo_base": 1000,
        "duracion_dias": 365,
        "dias_incluidos": "libre",
        "limite_dias_semana": None,
        "dias_por_semana": None,
        "horas_por_clase": None,
        "nivel_competitivo": False,
        "color": "#8b5cf6",
        "permite_dias_extra": False,
        "costo_dia_extra": None,
        "costo_dia_extra_sabado": None,
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
