"""
API Gateway v3 — Auth JWT + gestion profil admin + reset mot de passe
Port: 3000
"""
import os, time, logging, json, hashlib, secrets
from datetime import datetime, timedelta
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import text
from db import get_db, test_connection

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-gateway")

app = FastAPI(title="API Gateway — Pharmacies de Garde Tanger", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def on_startup():
    if test_connection():
        logger.info("✅ Connexion SQL Server établie.")
        load_users()  # crée l'admin par défaut si la table est vide
    else:
        logger.error("❌ Impossible de se connecter à SQL Server. Vérifiez DB_SERVER/DB_AUTH dans .env.")

PHARMACIE_URL = os.getenv("PHARMACIE_SERVICE_URL", "http://localhost:8001")
CHATBOT_URL   = os.getenv("CHATBOT_SERVICE_URL",   "http://localhost:8002")
JWT_SECRET    = os.getenv("JWT_SECRET", "pharmacie_tanger_secret_2026_changez_en_prod")
JWT_EXP_HOURS = 24


# ── Helpers users (SQL Server) ──────────────────────────────────────────────────
def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users() -> list:
    """Retourne tous les utilisateurs depuis la BDD. Crée l'admin par défaut si la table est vide."""
    with get_db() as db:
        rows = db.execute(text(
            "SELECT id, nom, email, password_hash, role FROM utilisateurs"
        )).fetchall()

        if not rows:
            db.execute(text("""
                INSERT INTO utilisateurs (nom, email, password_hash, role)
                VALUES (:nom, :email, :password_hash, :role)
            """), {"nom": "Admin", "email": "admin@gmail.com",
                   "password_hash": hash_pw("admin123"), "role": "admin"})
            rows = db.execute(text(
                "SELECT id, nom, email, password_hash, role FROM utilisateurs"
            )).fetchall()

    return [{"id": r.id, "nom": r.nom, "email": r.email,
             "password_hash": r.password_hash, "role": r.role} for r in rows]

def save_users(users: list):
    """Met à jour chaque utilisateur de la liste en base (update par id)."""
    with get_db() as db:
        for u in users:
            db.execute(text("""
                UPDATE utilisateurs
                SET nom = :nom, email = :email, password_hash = :password_hash, role = :role
                WHERE id = :id
            """), {"id": u["id"], "nom": u["nom"], "email": u["email"],
                   "password_hash": u["password_hash"], "role": u["role"]})

def create_token(user: dict) -> str:
    payload = {"sub": user["id"], "email": user["email"], "nom": user["nom"],
               "role": user["role"], "exp": (datetime.utcnow() + timedelta(hours=JWT_EXP_HOURS)).timestamp()}
    if JWT_AVAILABLE: return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    import base64
    return base64.b64encode(json.dumps(payload).encode()).decode()

def verify_token(token: str) -> Optional[dict]:
    try:
        if JWT_AVAILABLE: payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        else:
            import base64
            payload = json.loads(base64.b64decode(token.encode()).decode())
        if payload.get("exp", 0) < datetime.utcnow().timestamp(): return None
        return payload
    except: return None


# ── Rate limiting ─────────────────────────────────────────────────────────────
req_counts: dict = {}
banned_ips: dict = {}  # ip -> ban_until_timestamp

def check_rate_limit(ip: str, limit: int) -> bool:
    now = time.time()
    req_counts.setdefault(ip, [])
    req_counts[ip] = [t for t in req_counts[ip] if now - t < 60]
    if len(req_counts[ip]) >= limit:
        return False
    req_counts[ip].append(now)
    return True

@app.middleware("http")
async def log_mw(request: Request, call_next):
    start = time.time()
    ip = request.client.host if request.client else "unknown"
    now = time.time()

    # 1. Vérification du bannissement temporaire
    if ip in banned_ips:
        if now < banned_ips[ip]:
            remaining = int(banned_ips[ip] - now)
            return JSONResponse(
                status_code=429,
                content={"detail": f"IP temporairement bannie pour abus. Réessayez dans {remaining} secondes."}
            )
        else:
            del banned_ips[ip]

    # 2. Application du Rate Limiting sur les routes /api
    path = request.url.path
    if path.startswith("/api"):
        limit = 60 if "/api/chat" in path else 100
        if not check_rate_limit(ip, limit):
            banned_ips[ip] = now + 900  # Bannir pour 15 minutes (900 secondes)
            logger.warning(f"⚠️ IP {ip} bannie pour 15 minutes (seuil dépassé sur {path})")
            return JSONResponse(
                status_code=429,
                content={"detail": "Trop de requêtes. Votre IP a été bannie pour 15 minutes."}
            )

    resp = await call_next(request)
    logger.info(f"{ip} {request.method} {request.url.path} → {resp.status_code} ({(time.time()-start)*1000:.0f}ms)")
    return resp


# ── Auth helpers ──────────────────────────────────────────────────────────────
security = HTTPBearer(auto_error=False)

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    if not creds: raise HTTPException(401, "Token requis")
    payload = verify_token(creds.credentials)
    if not payload: raise HTTPException(401, "Token invalide ou expiré")
    return payload

def require_admin(creds: HTTPAuthorizationCredentials = Depends(security)):
    user = get_current_user(creds)
    if user.get("role") != "admin": raise HTTPException(403, "Accès admin requis")
    return user


# ── Proxy helpers ─────────────────────────────────────────────────────────────
async def proxy_get(url: str, params: dict = None):
    async with httpx.AsyncClient(timeout=15.0) as c:
        try:
            r = await c.get(url, params=params); r.raise_for_status(); return r.json()
        except httpx.ConnectError: raise HTTPException(503, "Service indisponible")
        except httpx.HTTPStatusError as e: raise HTTPException(e.response.status_code, e.response.text)

async def proxy_post(url: str, body: dict):
    async with httpx.AsyncClient(timeout=60.0) as c:
        try:
            r = await c.post(url, json=body); r.raise_for_status(); return r.json()
        except httpx.ConnectError: raise HTTPException(503, "Service indisponible")
        except httpx.HTTPStatusError as e: raise HTTPException(e.response.status_code, e.response.text)


# ── Routes de base ────────────────────────────────────────────────────────────
@app.get("/")
def root(): return {"service": "API Gateway", "version": "3.0.0"}

@app.get("/health")
async def health():
    services = {}
    async with httpx.AsyncClient(timeout=5.0) as c:
        for name, url in [("pharmacie-service", f"{PHARMACIE_URL}/health"),
                          ("chatbot-service", f"{CHATBOT_URL}/health")]:
            try:
                r = await c.get(url)
                services[name] = "ok" if r.status_code == 200 else "degraded"
            except: services[name] = "unreachable"
    db_ok = test_connection()
    return {"status": "ok" if all(v=="ok" for v in services.values()) and db_ok else "degraded",
            "gateway": "ok", "database": "ok" if db_ok else "unreachable", "services": services}


# ── Auth ──────────────────────────────────────────────────────────────────────
class LoginReq(BaseModel):
    email: str
    password: str

@app.post("/api/auth/login")
def login(body: LoginReq):
    users = load_users()
    user = next((u for u in users if u["email"] == body.email
                 and u["password_hash"] == hash_pw(body.password)), None)
    if not user: raise HTTPException(401, "Email ou mot de passe incorrect")
    return {"token": create_token(user),
            "user": {"id": user["id"], "email": user["email"], "nom": user["nom"], "role": user["role"]}}

@app.get("/api/auth/me")
def me(user=Depends(get_current_user)): return user


# ── Profil admin : changer email et/ou mot de passe ──────────────────────────
class UpdateProfileReq(BaseModel):
    nom: Optional[str] = None
    email: Optional[str] = None
    current_password: str
    new_password: Optional[str] = None

@app.put("/api/admin/profile")
def update_profile(body: UpdateProfileReq, user=Depends(require_admin)):
    users = load_users()
    idx = next((i for i, u in enumerate(users) if u["id"] == user["sub"]), None)
    if idx is None: raise HTTPException(404, "Utilisateur introuvable")

    # Vérifier le mot de passe actuel
    if users[idx]["password_hash"] != hash_pw(body.current_password):
        raise HTTPException(401, "Mot de passe actuel incorrect")

    # Vérifier unicité email
    if body.email and body.email != users[idx]["email"]:
        if any(u["email"] == body.email and u["id"] != user["sub"] for u in users):
            raise HTTPException(409, "Cet email est déjà utilisé")
        users[idx]["email"] = body.email

    if body.nom:
        users[idx]["nom"] = body.nom

    if body.new_password:
        if len(body.new_password) < 6:
            raise HTTPException(400, "Nouveau mot de passe trop court (min 6 caractères)")
        users[idx]["password_hash"] = hash_pw(body.new_password)

    save_users(users)
    new_token = create_token(users[idx])
    return {"message": "✅ Profil mis à jour avec succès",
            "token": new_token,
            "user": {"id": users[idx]["id"], "email": users[idx]["email"],
                     "nom": users[idx]["nom"], "role": users[idx]["role"]}}


# ── Réinitialisation mot de passe (oubli) ────────────────────────────────────
@app.post("/api/auth/forgot-password")
def forgot_password(body: LoginReq):
    """Génère un token de reset — en prod, envoyer par email; ici on le retourne."""
    users = load_users()
    user = next((u for u in users if u["email"] == body.email), None)
    # On ne révèle pas si l'email existe (sécurité)
    if not user:
        return {"message": "Si cet email existe, un token de réinitialisation a été généré.",
                "reset_token": None}

    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)

    with get_db() as db:
        db.execute(text("""
            INSERT INTO reset_tokens (token, user_id, email, expires)
            VALUES (:token, :user_id, :email, :expires)
        """), {"token": token, "user_id": user["id"], "email": user["email"], "expires": expires})

    logger.info(f"Reset token pour {user['email']}: {token}")
    # En développement, on retourne le token directement
    return {"message": "Token de réinitialisation généré.",
            "reset_token": token,
            "expires_in": "1 heure",
            "note": "En production, ce token serait envoyé par email"}

class ResetPasswordReq(BaseModel):
    reset_token: str
    new_password: str

@app.post("/api/auth/reset-password")
def reset_password(body: ResetPasswordReq):
    with get_db() as db:
        row = db.execute(text(
            "SELECT user_id, email, expires FROM reset_tokens WHERE token = :token"
        ), {"token": body.reset_token}).fetchone()

    if not row: raise HTTPException(400, "Token invalide ou expiré")

    if datetime.utcnow() > row.expires:
        with get_db() as db:
            db.execute(text("DELETE FROM reset_tokens WHERE token = :token"), {"token": body.reset_token})
        raise HTTPException(400, "Token expiré. Recommencez la procédure.")

    if len(body.new_password) < 6:
        raise HTTPException(400, "Mot de passe trop court (min 6 caractères)")

    users = load_users()
    idx = next((i for i, u in enumerate(users) if u["id"] == row.user_id), None)
    if idx is None: raise HTTPException(404, "Utilisateur introuvable")

    users[idx]["password_hash"] = hash_pw(body.new_password)
    save_users(users)

    # Invalider le token
    with get_db() as db:
        db.execute(text("DELETE FROM reset_tokens WHERE token = :token"), {"token": body.reset_token})

    return {"message": "✅ Mot de passe réinitialisé avec succès. Vous pouvez vous connecter."}


# ── Routes Gardes (publiques) ─────────────────────────────────────────────────
@app.get("/api/gardes")
async def get_gardes(request: Request):
    return await proxy_get(f"{PHARMACIE_URL}/gardes", dict(request.query_params))

@app.get("/api/gardes/today")
async def get_today(): return await proxy_get(f"{PHARMACIE_URL}/gardes/today")

@app.get("/api/gardes/dates")
async def get_dates(): return await proxy_get(f"{PHARMACIE_URL}/gardes/dates")

@app.get("/api/pharmacies")
async def get_pharmacies(request: Request):
    return await proxy_get(f"{PHARMACIE_URL}/pharmacies", dict(request.query_params))

@app.get("/api/pharmacies/{nom}")
async def get_pharmacie(nom: str): return await proxy_get(f"{PHARMACIE_URL}/pharmacies/{nom}")

@app.get("/api/trimestre")
async def get_trimestre(): return await proxy_get(f"{PHARMACIE_URL}/trimestre")

@app.get("/api/stats")
async def get_stats(): return await proxy_get(f"{PHARMACIE_URL}/stats")


# ── Routes Admin (protégées) ──────────────────────────────────────────────────
@app.post("/api/admin/trimestre/import")
async def import_pdf(file: UploadFile = File(...), admin=Depends(require_admin)):
    if not file.filename.lower().endswith(".pdf"): raise HTTPException(400, "PDF requis")
    content = await file.read()
    async with httpx.AsyncClient(timeout=60.0) as c:
        try:
            r = await c.post(f"{PHARMACIE_URL}/trimestre/import",
                             files={"file": (file.filename, content, "application/pdf")})
            r.raise_for_status(); return r.json()
        except httpx.ConnectError: raise HTTPException(503, "Service pharmacie indisponible")
        except httpx.HTTPStatusError as e: raise HTTPException(e.response.status_code, e.response.text)


# ── Chatbot ───────────────────────────────────────────────────────────────────
class ChatReq(BaseModel):
    model: Optional[str] = "claude-sonnet-4-20250514"
    max_tokens: Optional[int] = 1000
    messages: List[dict]
    system: Optional[str] = None

@app.post("/api/chat")
async def chat(body: ChatReq):
    return await proxy_post(f"{CHATBOT_URL}/chat", {
        "messages": body.messages, "max_tokens": body.max_tokens, "model": body.model
    })
