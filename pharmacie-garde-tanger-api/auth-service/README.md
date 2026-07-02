# auth-service (Spring Boot)

Microservice d'authentification écrit en Java/Spring Boot — c'est le service "minimum Spring Boot"
exigé par le sujet du projet. Les autres microservices (api-gateway, pharmacie-service, chatbot-service)
sont en Python/FastAPI.

Il partage la **même table `utilisateurs`** dans SQL Server que `api-gateway`, avec le même algorithme
de hash de mot de passe (SHA-256) et le même secret JWT — un compte créé par l'un est utilisable
par l'autre.

## Lancer en local sous Windows (Windows Authentication)

Par défaut, `application.properties` utilise `integratedSecurity=true`, c'est-à-dire ton compte
Windows actuel, sans mot de passe. C'est la même config que `pharmacie-service`/`api-gateway` en local.

**Étape obligatoire avant de lancer** : le driver `mssql-jdbc` a besoin d'un petit fichier `.dll`
pour utiliser `integratedSecurity=true` (Java seul ne sait pas parler "compte Windows", il délègue
à cette DLL native).

1. Télécharge le pilote JDBC Microsoft :
   https://learn.microsoft.com/sql/connect/jdbc/download-microsoft-jdbc-driver-for-sql-server
2. Dans l'archive téléchargée, trouve le fichier `mssql-jdbc_auth-<version>-x64.dll`
   (dossier `auth/x64`)
3. Copie ce fichier dans : `C:\Windows\System32\`
   (ou ajoute son dossier à la variable d'environnement PATH)
4. Relance ton terminal pour que le changement soit pris en compte.

Ensuite, lance le service normalement :

```powershell
cd auth-service
mvn spring-boot:run
```

Si tu vois `✅` dans les logs au démarrage (ou pas d'erreur `Login failed`/`IM002`), la connexion
à SQL Server fonctionne. Le service écoute sur `http://localhost:8080`.

## Lancer avec Docker

Docker (Linux) ne peut pas utiliser ton compte Windows. `docker-compose.yml` bascule donc
automatiquement ce service en authentification SQL Server classique via les variables
d'environnement `DB_AUTH=sql`, `DB_USER`, `DB_PASSWORD` définies dans `.env` à la racine
de `pharmacie-garde-tanger-api/`.

```bash
docker compose up --build auth-service
```

## Tester rapidement

```powershell
# Connexion avec le compte admin par défaut (créé par database/init_sqlserver.sql)
curl -X POST http://localhost:8080/api/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"admin@gmail.com","password":"admin123"}'
```

## Routes disponibles

| Méthode | Route | Description |
|---|---|---|
| GET | `/api/auth/health` | Vérifie que le service tourne |
| POST | `/api/auth/login` | Connexion (email + password) → token JWT |
| POST | `/api/auth/register` | Création d'un compte utilisateur (role "user") |
| POST | `/api/auth/validate` | Vérifie la validité d'un token JWT |
