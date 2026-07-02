# 🏥 Pharmacies de Garde Tanger — Backend Microservices v4

## Architecture

```
Frontend Angular (4200)
        |
API Gateway (3000) — Auth JWT, profil admin, reset password, rate limiting
   /         |          \
pharmacie-  chatbot-     auth-service (8080)
service     service      Spring Boot / Java
 (8001)      (8002)      compte admin, login,
 - gardes    - proxy     register, validate token
 - import      Claude IA
   PDF
        \         /
       SQL Server (pharmacie_db)
       tables: utilisateurs, pharmacies, gardes,
               trimestre_meta, reset_tokens
```

`pharmacie-service` et `api-gateway` (Python) ainsi que `auth-service` (Java) lisent/écrivent
dans la **même base SQL Server**, ce qui en fait une vraie architecture microservices avec
persistance partagée (au lieu des fichiers JSON utilisés dans les versions précédentes).

## Nouveautés v4

- ✅ **Migration complète vers SQL Server** : toutes les données (utilisateurs, pharmacies,
  gardes, trimestre, tokens de reset) sont en base relationnelle, plus de fichiers `.json`
- ✅ **`auth-service` en Spring Boot** : microservice Java dédié à l'authentification,
  satisfait l'exigence "au moins un service Spring Boot" du sujet
- ✅ **Compatibilité Java ↔ Python** : même algorithme de hash (SHA-256), même secret JWT —
  un compte créé/connecté via l'un des deux fonctionne avec l'autre

## Démarrage — en local sous Windows (recommandé pendant le développement)

**Étape 0 — créer la base de données (une seule fois)**
Ouvre SSMS, connecte-toi (Windows Authentication), ouvre `database/init_sqlserver.sql`,
clique sur "Execute". Ça crée `pharmacie_db` et toutes les tables.

**Étape 1 — installer les dépendances (une seule fois par service)**
```powershell
cd pharmacie-service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

cd ..\api-gateway
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

cd ..\chatbot-service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Pour `auth-service` (Java), installe la DLL Windows Authentication — voir
`auth-service/README.md`, c'est une étape obligatoire unique.

**Étape 2 — lancer les 4 services**

Option A — un script qui ouvre les 4 fenêtres automatiquement :
```powershell
.\start-local.ps1
```

Option B — manuellement, 4 terminaux PowerShell séparés :
```powershell
# Terminal 1
cd auth-service
mvn spring-boot:run

# Terminal 2
cd pharmacie-service
venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 3
cd chatbot-service
venv\Scripts\activate
$env:ANTHROPIC_API_KEY="ta-cle-ici"
uvicorn main:app --host 0.0.0.0 --port 8002 --reload

# Terminal 4
cd api-gateway
venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 3000 --reload
```

**Étape 3 — vérifier**
Ouvre `http://localhost:3000/health` dans ton navigateur : tu dois voir
`"database": "ok"` et les 2 services Python en `"ok"`.

## Démarrage — avec Docker (déploiement / démo complète)

Docker inclut son propre conteneur SQL Server (les conteneurs Linux ne peuvent pas
utiliser ton compte Windows) :

```bash
docker compose up --build
```

Ça démarre, dans l'ordre : SQL Server → initialisation des tables → les 4 microservices.

## Compte admin par défaut

```
Email    : admin@gmail.com
Password : admin123
```

## Endpoints clés

| Méthode | Route | Service | Auth | Description |
|---------|-------|---------|------|-------------|
| POST | `/api/auth/login` | api-gateway (3000) | non | Connexion |
| POST | `/api/auth/forgot-password` | api-gateway | non | Demande reset (retourne le token en dev) |
| POST | `/api/auth/reset-password` | api-gateway | non | Confirme le reset avec le token |
| PUT  | `/api/admin/profile` | api-gateway | admin | Modifier nom/email/mot de passe |
| POST | `/api/admin/trimestre/import` | api-gateway → pharmacie-service | admin | Upload PDF planning |
| GET  | `/api/gardes/today` | api-gateway → pharmacie-service | non | Gardes du jour |
| GET  | `/api/pharmacies` | api-gateway → pharmacie-service | non | Liste pharmacies (statiques + dynamiques) |
| GET  | `/api/trimestre` | api-gateway → pharmacie-service | non | Statut trimestre + alertes |
| POST | `/api/auth/login` | auth-service (8080, direct) | non | Connexion alternative via Spring Boot |
| POST | `/api/auth/register` | auth-service (8080, direct) | non | Créer un compte utilisateur |
| POST | `/api/auth/validate` | auth-service (8080, direct) | non | Vérifier un token JWT |

> Le frontend Angular utilise `api-gateway` (port 3000) comme point d'entrée unique.
> `auth-service` (port 8080) existe en tant que microservice Spring Boot indépendant,
> démontrant l'architecture microservices polyglotte (Java + Python) demandée par le sujet.

