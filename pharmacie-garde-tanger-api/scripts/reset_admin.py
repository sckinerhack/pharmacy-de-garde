"""
Script utilitaire : réinitialise le compte admin par défaut dans SQL Server.
Usage : python scripts/reset_admin.py
À lancer depuis le dossier pharmacie-garde-tanger-api/, avec le même venv
que api-gateway (besoin de SQLAlchemy + pyodbc : pip install -r api-gateway/requirements.txt).
"""
import hashlib
import sys
from pathlib import Path

# Permet d'importer db.py depuis api-gateway/ sans dupliquer le code
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api-gateway"))

from db import get_db, test_connection  # noqa: E402
from sqlalchemy import text  # noqa: E402


def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def main():
    if not test_connection():
        print("❌ Connexion à SQL Server impossible. Vérifie que la base existe "
              "(database/init_sqlserver.sql) et que DB_AUTH/DB_SERVER sont corrects.")
        return

    password_hash = hash_pw("admin123")

    with get_db() as db:
        existing = db.execute(
            text("SELECT id FROM utilisateurs WHERE email = :email"),
            {"email": "admin@gmail.com"},
        ).fetchone()

        if existing:
            db.execute(
                text("UPDATE utilisateurs SET password_hash = :hash, role = 'admin' WHERE email = :email"),
                {"hash": password_hash, "email": "admin@gmail.com"},
            )
            print("✅ Mot de passe de l'admin existant réinitialisé.")
        else:
            db.execute(
                text(
                    "INSERT INTO utilisateurs (nom, email, password_hash, role) "
                    "VALUES ('Admin', 'admin@gmail.com', :hash, 'admin')"
                ),
                {"hash": password_hash},
            )
            print("✅ Compte admin créé.")

    print("Email    : admin@gmail.com")
    print("Password : admin123")


if __name__ == "__main__":
    main()
