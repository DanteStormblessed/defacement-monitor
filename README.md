# Defacement Monitor

Aplicación web para monitorear cambios (defacement) en sitios web autorizados.

## Arquitectura (MVP)
- **frontend/**: UI (placeholder por ahora)
- **target-manager/**: API (FastAPI) que gestiona targets, autenticación y resultados de escaneo
- **scanner/**: bot ejecutado por GitHub Actions que obtiene targets pendientes y reporta resultados
- **.github/workflows/**: cron del scanner y CI básico del backend
- **k8s/**: manifiestos base (AKS / Kubernetes)

> Nota ética/seguridad: este proyecto es para monitoreo autorizado. El scanner implementa navegación robusta y “polite scraping” (timeouts, user-agent configurable, rate limiting). No incluye técnicas de bypass de controles de seguridad.

## Quickstart (local)

### 1) Levantar el Target Manager

En una terminal (PowerShell):

```powershell
cd target-manager
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:JWT_SECRET = "dev-secret"
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = "admin"
$env:SCANNER_API_KEY = "scanner-dev-key"
uvicorn app.main:app --reload --port 8000
```

### Configurar PostgreSQL (opcional)

El backend soporta PostgreSQL configurando `DATABASE_URL`.

Formato recomendado:
`postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`

Ejemplos:
- Local con Docker: `postgresql+psycopg://postgres:postgres@localhost:5432/defacement`
- Azure Database for PostgreSQL: `postgresql+psycopg://user:pass@myserver.postgres.database.azure.com:5432/defacement`

Para levantar Postgres local rápido:

```powershell
docker compose up -d postgres
$env:DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/defacement"
cd target-manager
uvicorn app.main:app --reload --port 8000
```

## Build & Push de la imagen (ACR)

En algunas regiones (por ejemplo `chilecentral`) el comando `az acr build` (ACR Tasks) puede no estar disponible.
En ese caso usa build local + push:

```powershell
az acr login -n defacementmonitoracr
docker build -t defacementmonitoracr.azurecr.io/target-manager:0.1.0 -f target-manager/Dockerfile target-manager
docker push defacementmonitoracr.azurecr.io/target-manager:0.1.0
```
```

API: `http://localhost:8000`  
Docs: `http://localhost:8000/docs`

### 2) Crear un target

1) Obtener token JWT:

```powershell
curl -Method POST "http://localhost:8000/api/v1/auth/token-json" -ContentType "application/json" -Body '{"username":"admin","password":"admin"}'
```

2) Crear target:

```powershell
$token = "<pega_aqui_el_access_token>"
curl -Method POST "http://localhost:8000/api/v1/targets" -Headers @{ Authorization = "Bearer $token" } -ContentType "application/json" -Body '{"name":"Example","url":"https://example.org","scan_interval_seconds":1800}'
```

### 3) Ejecutar el scanner en modo local

```powershell
cd ..\scanner
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:TARGET_MANAGER_URL = "http://localhost:8000"
$env:SCANNER_API_KEY = "scanner-dev-key"
python .\scanner_bot.py
```

## Endpoints clave (Core)
- `GET /api/v1/targets/pending-scan` (API Key del bot)
- `POST /api/v1/scan-results` (API Key del bot)
- `POST /api/v1/auth/token` (JWT admin)
- `POST /api/v1/targets` (JWT admin)
