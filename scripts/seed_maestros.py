"""
Seed de usuarios admin y maestros reales de Katira's Gymnastics.
Trunca las tablas users y maestros, luego inserta los datos reales.

Ejecutar: python scripts/seed_maestros.py
"""
import secrets
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models import Maestro, User

ADMINS = [
    {"username": "KOrtiz",    "password": "KOrtiz",    "full_name": "Kate Ortiz"},
    {"username": "Admin",     "password": "ChrisK84",  "full_name": "Administrador"},
]

MAESTROS = [
    {
        "nombre": "Fernanda Gabriela", "apellido_paterno": "Flores",
        "apellido_materno": "Rodriguez", "telefono": "6567797002",
        "fecha_nacimiento": date(2004, 11, 15),
    },
    {
        "nombre": "Natalia Cecilia", "apellido_paterno": "Salas",
        "apellido_materno": "Montana", "telefono": "6568629432",
        "fecha_nacimiento": date(2005, 6, 14),
    },
    {
        "nombre": "Ana Grecia", "apellido_paterno": "Espinoza",
        "apellido_materno": "Chavero", "telefono": "6564371173",
        "fecha_nacimiento": date(2006, 7, 5),
    },
    {
        "nombre": "Oscar", "apellido_paterno": "Jaquez",
        "apellido_materno": "Davila", "telefono": "6562781375",
        "fecha_nacimiento": date(1976, 6, 18),
    },
    {
        "nombre": "Danara Jacqueline", "apellido_paterno": "Espinoza",
        "apellido_materno": "Chavero", "telefono": "6564376925",
        "fecha_nacimiento": date(2002, 12, 12),
    },
    {
        "nombre": "Martha Elena", "apellido_paterno": "Portillo",
        "apellido_materno": "Lopez", "telefono": "6561386887",
        "fecha_nacimiento": date(1961, 7, 26),
    },
]


def _generar_username(nombre: str, apellido_paterno: str) -> str:
    return nombre.split()[0][0].upper() + apellido_paterno[0].upper() + apellido_paterno[1:].lower()


def _generar_password() -> str:
    return secrets.token_urlsafe(8)


def main():
    print("Creando tablas si no existen...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("TRUNCANDO maestros...")
        db.execute(Maestro.__table__.delete())
        print("TRUNCANDO users...")
        db.execute(User.__table__.delete())
        db.commit()

        print("\nInsertando usuarios ADMIN:")
        for admin in ADMINS:
            u = User(
                username=admin["username"],
                password_hash=hash_password(admin["password"]),
                full_name=admin["full_name"],
                role_id=1,
            )
            db.add(u)
            db.flush()
            print(f"  {u.username} (id={u.id}) → role=Admin")

        print("\nInsertando MAESTROS con usuarios auto-generados:")
        for m in MAESTROS:
            username = _generar_username(m["nombre"], m["apellido_paterno"])
            password = _generar_password()

            u = User(
                username=username,
                password_hash=hash_password(password),
                full_name=f"{m['nombre']} {m['apellido_paterno']} {m['apellido_materno']}",
                role_id=2,
            )
            db.add(u)
            db.flush()

            maestro = Maestro(
                user_id=u.id,
                nombre=m["nombre"],
                apellido_paterno=m["apellido_paterno"],
                apellido_materno=m["apellido_materno"],
                telefono=m["telefono"],
                fecha_nacimiento=m["fecha_nacimiento"],
            )
            db.add(maestro)
            db.flush()
            print(f"  {username} / {password} (user_id={u.id}, maestro_id={maestro.id})")

        db.commit()
        print("\nSeed completado exitosamente.")

    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
