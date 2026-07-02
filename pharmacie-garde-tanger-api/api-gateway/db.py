"""
Connexion à la base de données SQL Server pour api-gateway.
Utilise SQLAlchemy + pyodbc.
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

DB_SERVER   = os.getenv("DB_SERVER", "localhost")
DB_NAME     = os.getenv("DB_NAME", "pharmacie_db")
DB_DRIVER   = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
# Authentification : "windows" (compte Windows, par défaut) ou "sql" (login/mot de passe)
DB_AUTH     = os.getenv("DB_AUTH", "windows")
DB_USER     = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

if DB_AUTH == "windows":
    # Connexion via authentification Windows (Trusted_Connection) — pas de mot de passe
    CONN_STR = (
        f"mssql+pyodbc://@{DB_SERVER}/{DB_NAME}"
        f"?driver={DB_DRIVER.replace(' ', '+')}&trusted_connection=yes&TrustServerCertificate=yes"
    )
else:
    # Connexion via authentification SQL Server (utilisateur/mot de passe)
    CONN_STR = (
        f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}/{DB_NAME}"
        f"?driver={DB_DRIVER.replace(' ', '+')}&TrustServerCertificate=yes"
    )

engine = create_engine(CONN_STR, pool_pre_ping=True, fast_executemany=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def get_db():
    """Fournit une session DB, la ferme automatiquement après usage."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def test_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        msg = str(e)
        if "IM002" in msg or "Data source name not found" in msg:
            print("❌ Driver ODBC introuvable. Installe 'ODBC Driver 17 for SQL Server' "
                  "depuis https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server "
                  "puis relance le service.")
        elif "Login failed" in msg:
            print("❌ Connexion refusée par SQL Server. Vérifie DB_AUTH/DB_USER/DB_PASSWORD, "
                  "ou que ton compte Windows a accès à la base dans SSMS (Security > Logins).")
        else:
            print(f"❌ Erreur connexion SQL Server: {e}")
        return False
