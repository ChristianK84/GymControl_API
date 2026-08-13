"""
Migración: agregar requires_firma a reglamentos, fecha_lectura a firmas_reglamento,
y hacer nullable user_id en audit_logs para acciones públicas.
Ejecutar una vez contra la base de datos de producción (Supabase).

Uso:
  python -m scripts.migrate_reglamentos_lectura
"""
import sys
from sqlalchemy import text
from app.core.database import engine


def migrate():
    with engine.begin() as conn:
        # Agregar requires_firma a reglamentos
        conn.execute(text(
            "ALTER TABLE reglamentos ADD COLUMN IF NOT EXISTS requires_firma BOOLEAN DEFAULT TRUE"
        ))
        print("OK: reglamentos.requires_firma agregada")

        # Agregar fecha_lectura a firmas_reglamento
        conn.execute(text(
            "ALTER TABLE firmas_reglamento ADD COLUMN IF NOT EXISTS fecha_lectura TIMESTAMP NULL"
        ))
        print("OK: firmas_reglamento.fecha_lectura agregada")

        # Hacer nullable user_id en audit_logs (acciones públicas sin usuario)
        conn.execute(text(
            "ALTER TABLE audit_logs ALTER COLUMN user_id DROP NOT NULL"
        ))
        print("OK: audit_logs.user_id ahora es nullable")

    print("Migración completada.")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"Error en migración: {e}", file=sys.stderr)
        sys.exit(1)
