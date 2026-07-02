"""
Microservice: Pharmacie Service
Port: 8001 — Gestion des gardes + import PDF + enregistrement pharmacies nouvelles
"""
import os, re, json, logging
from pathlib import Path
from datetime import date, datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from data.pharmacies_details import PHARMACIES_DETAILS as PHARMACIES_STATIQUES
from db import get_db, test_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pharmacie-service")

app = FastAPI(title="Pharmacie Service", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Modèles ───────────────────────────────────────────────────────────────────
class PharmacieDetail(BaseModel):
    nom: str
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    has_detail: bool = False

class JourGarde(BaseModel):
    date: str
    type: str
    pharmacies: List[str]

class GardeResponse(BaseModel):
    date: str
    gardes: List[JourGarde]
    total_pharmacies: int
    is_today: bool

class TrimestreInfo(BaseModel):
    debut: str
    fin: str
    jours_restants: int
    alerte: bool
    alerte_message: Optional[str] = None
    donnees_disponibles: bool
    upload_date: Optional[str] = None

class ImportResult(BaseModel):
    success: bool
    message: str
    jours_importes: int
    periode: dict
    nouvelles_pharmacies: int = 0


# ── DB Helpers (SQL Server) ─────────────────────────────────────────────────────
def fmt(d: date) -> str: return d.strftime("%d/%m/%Y")

def parse_d(s: str) -> date: return datetime.strptime(s, "%d/%m/%Y").date()


def seed_database():
    """Insère les pharmacies statiques et l'admin par défaut si la table est vide.
       Appelé une seule fois au démarrage du service."""
    with get_db() as db:
        count = db.execute(text("SELECT COUNT(*) FROM pharmacies")).scalar()
        if count == 0:
            inserted_noms = set()
            for p in PHARMACIES_STATIQUES:
                nom_upper = p["nom"].upper()
                if nom_upper in inserted_noms:
                    continue
                db.execute(text("""
                    INSERT INTO pharmacies (nom, adresse, telephone, lat, lng, source)
                    VALUES (:nom, :adresse, :telephone, :lat, :lng, 'statique')
                """), {
                    "nom": p["nom"], "adresse": p.get("adresse"),
                    "telephone": p.get("telephone"), "lat": p.get("lat"), "lng": p.get("lng")
                })
                inserted_noms.add(nom_upper)
            logger.info(f"Seed: {len(inserted_noms)} pharmacies statiques insérées.")


def load_gardes() -> list:
    """Retourne toutes les gardes, regroupées par (date, type) comme dans le JSON d'origine."""
    with get_db() as db:
        rows = db.execute(text(
            "SELECT date_garde, type_garde, pharmacie_nom FROM gardes ORDER BY date_garde"
        )).fetchall()

    grouped: dict = {}
    for r in rows:
        date_str = fmt(r.date_garde) if isinstance(r.date_garde, date) else r.date_garde
        key = (date_str, r.type_garde)
        grouped.setdefault(key, []).append(r.pharmacie_nom)

    return [{"date": k[0], "type": k[1], "pharmacies": v} for k, v in grouped.items()]


def load_meta() -> dict:
    with get_db() as db:
        row = db.execute(text(
            "SELECT TOP 1 upload_date, filename, debut, fin, jours_importes "
            "FROM trimestre_meta ORDER BY id DESC"
        )).fetchone()
    if not row:
        return {}
    return {
        "upload_date": row.upload_date,
        "filename": row.filename,
        "debut": fmt(row.debut) if row.debut else None,
        "fin": fmt(row.fin) if row.fin else None,
        "jours_importes": row.jours_importes,
    }


def load_pharmacies_dyn() -> list:
    """Pharmacies ajoutées dynamiquement via un import PDF (source = 'pdf')."""
    with get_db() as db:
        rows = db.execute(text(
            "SELECT nom, adresse, telephone, lat, lng FROM pharmacies WHERE source = 'pdf'"
        )).fetchall()
    return [{"nom": r.nom, "adresse": r.adresse, "telephone": r.telephone,
             "lat": r.lat, "lng": r.lng} for r in rows]


def get_all_pharmacies_details() -> list:
    """Retourne toutes les pharmacies (statiques + détectées via PDF) depuis la BDD."""
    with get_db() as db:
        rows = db.execute(text(
            "SELECT nom, adresse, telephone, lat, lng FROM pharmacies"
        )).fetchall()
    return [{"nom": r.nom, "adresse": r.adresse, "telephone": r.telephone,
             "lat": r.lat, "lng": r.lng} for r in rows]


def save_gardes(gardes: list):
    """Remplace entièrement les gardes en base (équivalent de l'ancien save_json complet)."""
    with get_db() as db:
        db.execute(text("DELETE FROM gardes"))
        for g in gardes:
            d = parse_d(g["date"])
            for pharm in g["pharmacies"]:
                db.execute(text("""
                    INSERT INTO gardes (date_garde, type_garde, pharmacie_nom)
                    VALUES (:date_garde, :type_garde, :pharmacie_nom)
                """), {"date_garde": d, "type_garde": g["type"], "pharmacie_nom": pharm})


def save_meta(meta: dict):
    with get_db() as db:
        db.execute(text("""
            INSERT INTO trimestre_meta (upload_date, filename, debut, fin, jours_importes)
            VALUES (:upload_date, :filename, :debut, :fin, :jours_importes)
        """), {
            "upload_date": meta["upload_date"], "filename": meta["filename"],
            "debut": parse_d(meta["debut"]), "fin": parse_d(meta["fin"]),
            "jours_importes": meta["jours_importes"]
        })


def save_pharmacies_dyn(nouvelles: list):
    """Insère les nouvelles pharmacies détectées dans le PDF (ignore les doublons)."""
    if not nouvelles:
        return
    with get_db() as db:
        for p in nouvelles:
            exists = db.execute(text(
                "SELECT COUNT(*) FROM pharmacies WHERE nom = :nom"
            ), {"nom": p["nom"]}).scalar()
            if not exists:
                db.execute(text("""
                    INSERT INTO pharmacies (nom, adresse, telephone, lat, lng, source)
                    VALUES (:nom, :adresse, :telephone, :lat, :lng, 'pdf')
                """), {
                    "nom": p["nom"], "adresse": p.get("adresse"),
                    "telephone": p.get("telephone"), "lat": p.get("lat"), "lng": p.get("lng")
                })


# ── Statut trimestre ──────────────────────────────────────────────────────────
def trimestre_status() -> dict:
    meta  = load_meta()
    gardes = load_gardes()
    today = date.today()
    if not gardes or not meta:
        return {"donnees_disponibles": False, "debut": None, "fin": None,
                "jours_restants": None, "alerte": False, "upload_date": None,
                "alerte_message": "Aucune donnée. Importez le planning PDF du trimestre."}
    dates = sorted({g["date"] for g in gardes})
    debut_str, fin_str = dates[0], dates[-1]
    try:
        fin_date = parse_d(fin_str)
    except:
        return {"donnees_disponibles": False, "alerte": False, "debut": None, "fin": None,
                "jours_restants": None, "upload_date": None}
    if today > fin_date:
        return {"donnees_disponibles": False, "debut": debut_str, "fin": fin_str,
                "jours_restants": 0, "alerte": True, "upload_date": meta.get("upload_date"),
                "alerte_message": f"⚠️ Planning expiré (fin : {fin_str}). Importez le nouveau planning."}
    jours = (fin_date - today).days
    alerte = jours <= 14
    return {"donnees_disponibles": True, "debut": debut_str, "fin": fin_str,
            "jours_restants": jours, "alerte": alerte, "upload_date": meta.get("upload_date"),
            "alerte_message": (f"⚠️ Le planning expire dans {jours} jour(s) ({fin_str}). Préparez le PDF du prochain trimestre.") if alerte else None}


# ── Parser PDF ────────────────────────────────────────────────────────────────
def parse_planning_pdf(pdf_bytes: bytes) -> tuple[list, list]:
    """
    Retourne (gardes, nouvelles_pharmacies).
    Utilise les positions X des mots pour séparer les cellules du tableau.
    """
    import io
    try: import pdfplumber
    except ImportError: raise HTTPException(500, "pdfplumber non installé")

    gardes = []
    current_type = "GARDE_24H"
    current_date = None
    all_pharm_names = set()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            lines: dict = {}
            for w in words:
                y = round(w["top"] / 5) * 5
                lines.setdefault(y, []).append(w)

            for y in sorted(lines.keys()):
                lw = sorted(lines[y], key=lambda w: w["x0"])
                lt = " ".join(w["text"] for w in lw).strip()
                if not lt: continue
                if re.match(r"^\d+\s*/\s*\d+$", lt): continue
                if any(x in lt for x in ["Liste des", "SYNDICAT", "D'OFFICINE", "nقاب"]): continue

                if lt in ("GARDE_24H", "GARDE 24H"): current_type = "GARDE_24H"; continue
                if lt == "WEEKEND":                   current_type = "WEEKEND";   continue
                if lt in ("JOUR FERIE", "JOUR_FERIE","JOURS FERIES"): current_type = "JOUR_FERIE"; continue

                if re.match(r"^\d{2}/\d{2}/\d{4}$", lt):
                    current_date = lt; continue

                if current_date and lw:
                    pharmacies = []
                    cur = [lw[0]["text"]]
                    for i in range(1, len(lw)):
                        gap = lw[i]["x0"] - lw[i-1]["x1"]
                        if gap > 12:
                            p = " ".join(cur).strip()
                            if p and len(p) > 1: pharmacies.append(p)
                            cur = [lw[i]["text"]]
                        else:
                            cur.append(lw[i]["text"])
                    if cur:
                        p = " ".join(cur).strip()
                        if p and len(p) > 1: pharmacies.append(p)

                    pharmacies = [p for p in pharmacies if not re.match(r"^\d+$", p) and len(p) >= 2]
                    if pharmacies:
                        all_pharm_names.update(pharmacies)
                        ex = next((g for g in gardes if g["date"] == current_date and g["type"] == current_type), None)
                        if ex:
                            for ph in pharmacies:
                                if ph not in ex["pharmacies"]: ex["pharmacies"].append(ph)
                        else:
                            gardes.append({"date": current_date, "type": current_type, "pharmacies": pharmacies})

    try:
        gardes.sort(key=lambda g: datetime.strptime(g["date"], "%d/%m/%Y"))
    except: pass

    # Détecter les nouvelles pharmacies (pas dans la base statique ni dynamique)
    existing_noms = {p["nom"] for p in get_all_pharmacies_details()}
    nouvelles = []
    for nom in all_pharm_names:
        if nom not in existing_noms:
            nouvelles.append({"nom": nom, "adresse": None, "telephone": None, "lat": None, "lng": None})
            logger.info(f"Nouvelle pharmacie détectée: {nom}")

    return gardes, nouvelles


# ── Routes Health ─────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    if test_connection():
        logger.info("✅ Connexion SQL Server établie.")
        seed_database()
    else:
        logger.error("❌ Impossible de se connecter à SQL Server. Vérifiez DB_SERVER/DB_USER/DB_PASSWORD.")


@app.get("/health")
def health(): return {"status": "ok", "service": "pharmacie-service", "version": "3.0.0", "db": test_connection()}


# ── Routes Trimestre ──────────────────────────────────────────────────────────
@app.get("/trimestre", response_model=TrimestreInfo)
def get_trimestre():
    st = trimestre_status()
    return TrimestreInfo(
        debut=st.get("debut") or "", fin=st.get("fin") or "",
        jours_restants=st.get("jours_restants") or 0,
        alerte=st.get("alerte", False), alerte_message=st.get("alerte_message"),
        donnees_disponibles=st.get("donnees_disponibles", False),
        upload_date=st.get("upload_date")
    )

@app.post("/trimestre/import", response_model=ImportResult)
async def import_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Seuls les fichiers PDF sont acceptés.")
    content = await file.read()
    if not content: raise HTTPException(400, "Fichier PDF vide.")

    gardes, nouvelles = parse_planning_pdf(content)

    if not gardes: raise HTTPException(422, "Aucune donnée trouvée dans le PDF.")

    save_gardes(gardes)

    # Enregistrer les nouvelles pharmacies
    if nouvelles:
        save_pharmacies_dyn(nouvelles)

    dates = sorted({g["date"] for g in gardes})
    debut, fin = dates[0], dates[-1]
    save_meta({
        "upload_date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "filename": file.filename, "debut": debut, "fin": fin,
        "jours_importes": len(gardes)
    })

    logger.info(f"Import OK: {len(gardes)} jours, {debut}→{fin}, {len(nouvelles)} nouvelles pharmacies")
    return ImportResult(
        success=True,
        message=f"✅ Import réussi ! {len(gardes)} jours de garde importés.",
        jours_importes=len(gardes), periode={"debut": debut, "fin": fin},
        nouvelles_pharmacies=len(nouvelles)
    )


# ── Routes Gardes ─────────────────────────────────────────────────────────────
@app.get("/gardes/today")
def get_today():
    st = trimestre_status()
    today_str = fmt(date.today())
    if not st["donnees_disponibles"]:
        return {"date": today_str, "gardes": [], "total_pharmacies": 0,
                "is_today": True, "donnees_disponibles": False,
                "message": st.get("alerte_message"), "trimestre": st}
    gardes = [g for g in load_gardes() if g["date"] == today_str]
    return {"date": today_str, "gardes": gardes,
            "total_pharmacies": sum(len(g["pharmacies"]) for g in gardes),
            "is_today": True, "donnees_disponibles": True, "trimestre": st}

@app.get("/gardes", response_model=GardeResponse)
def get_gardes(
    date_param: Optional[str] = Query(None, alias="date"),
    recherche: Optional[str] = Query(None)
):
    st = trimestre_status()
    if not st["donnees_disponibles"]:
        return GardeResponse(date=fmt(date.today()), gardes=[], total_pharmacies=0, is_today=True)
    try: target = parse_d(date_param) if date_param else date.today()
    except ValueError: raise HTTPException(400, "Format invalide. Utilisez DD/MM/YYYY")
    date_str = fmt(target)
    gardes = [g for g in load_gardes() if g["date"] == date_str]
    if recherche:
        q = recherche.lower()
        gardes = [{**g, "pharmacies": [p for p in g["pharmacies"] if q in p.lower()]} for g in gardes]
        gardes = [g for g in gardes if g["pharmacies"]]
    total = sum(len(g["pharmacies"]) for g in gardes)
    return GardeResponse(date=date_str, gardes=[JourGarde(**g) for g in gardes],
                         total_pharmacies=total, is_today=(target == date.today()))

@app.get("/gardes/dates")
def get_dates():
    return {"dates": sorted({g["date"] for g in load_gardes()})}


# ── Routes Pharmacies ─────────────────────────────────────────────────────────
@app.get("/pharmacies", response_model=List[PharmacieDetail])
def get_pharmacies(recherche: Optional[str] = Query(None)):
    result = get_all_pharmacies_details()
    if recherche:
        q = recherche.lower()
        result = [p for p in result if q in p["nom"].lower()]
    return [PharmacieDetail(**p, has_detail=bool(p.get("adresse") or p.get("telephone") or p.get("lat"))) for p in result]

@app.get("/pharmacies/{nom}", response_model=PharmacieDetail)
def get_pharmacie(nom: str):
    all_p = get_all_pharmacies_details()
    d = next((p for p in all_p if p["nom"] == nom.upper()), None)
    if not d: raise HTTPException(404, f"Pharmacie '{nom}' introuvable")
    return PharmacieDetail(**d, has_detail=bool(d.get("adresse") or d.get("telephone") or d.get("lat")))

@app.get("/stats")
def stats():
    gardes = load_gardes()
    st = trimestre_status()
    today_str = fmt(date.today())
    all_p = get_all_pharmacies_details()
    return {
        "total_pharmacies_uniques": len({p for g in gardes for p in g["pharmacies"]}),
        "total_jours_garde": len({g["date"] for g in gardes}),
        "total_pharmacies_details": len(all_p),
        "garde_aujourd_hui": sum(len(g["pharmacies"]) for g in gardes if g["date"] == today_str),
        "donnees_disponibles": st["donnees_disponibles"], "trimestre": st
    }
