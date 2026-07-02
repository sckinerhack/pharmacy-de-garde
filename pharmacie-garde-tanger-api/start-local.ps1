# start-local.ps1
# Lance les 4 microservices en local (Windows Authentication pour SQL Server),
# chacun dans sa propre fenetre PowerShell. A executer depuis le dossier
# pharmacie-garde-tanger-api/.
#
# Pre-requis avant la 1ere execution :
#   - SQL Server + SSMS installes, base "pharmacie_db" creee (database/init_sqlserver.sql)
#   - pour pharmacie-service et api-gateway : un venv avec "pip install -r requirements.txt"
#     dans chacun des 2 dossiers
#   - pour auth-service : la DLL mssql-jdbc_auth installee (voir auth-service/README.md)
#   - ta cle ANTHROPIC_API_KEY pour le chatbot (a saisir ci-dessous ou en variable d'env)

$root = $PSScriptRoot

Write-Host "Demarrage des 4 microservices..." -ForegroundColor Cyan

# 1. auth-service (Spring Boot, port 8080)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\auth-service'; mvn spring-boot:run"

# 2. pharmacie-service (FastAPI, port 8001)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\pharmacie-service'; venv\Scripts\activate; uvicorn main:app --host 0.0.0.0 --port 8001 --reload"

# 3. chatbot-service (FastAPI, port 8002) — pense a definir ta cle Anthropic
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\chatbot-service'; venv\Scripts\activate; `$env:ANTHROPIC_API_KEY='COLLE_TA_CLE_ICI'; uvicorn main:app --host 0.0.0.0 --port 8002 --reload"

# 4. api-gateway (FastAPI, port 3000)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\api-gateway'; venv\Scripts\activate; uvicorn main:app --host 0.0.0.0 --port 3000 --reload"

Write-Host "Les 4 services demarrent dans des fenetres separees." -ForegroundColor Green
Write-Host "Verifie http://localhost:3000/health une fois tout demarre." -ForegroundColor Green
