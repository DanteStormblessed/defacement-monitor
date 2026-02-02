# Target Manager (FastAPI)

API que gestiona:
- Targets
- Autenticación (JWT admin + API Key scanner)
- Resultados de escaneo + detección básica de cambios

## Config
Env vars:
- `DATABASE_URL` (opcional) / `DATA_DIR` (default `data/`)
- `JWT_SECRET` (requerida)
- `SCANNER_API_KEY` (requerida)
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` (defaults `admin`/`admin` para dev)

### Configurar credenciales localmente (recomendado)

Crea un archivo `target-manager/.env` (puedes copiar de `.env.example`) y define allí tus credenciales.

Ejemplo con PostgreSQL en tu PC (localhost):

```
DATABASE_URL=postgresql+psycopg://mi_usuario:mi_password@localhost:5432/defacement
JWT_SECRET=dev-secret
SCANNER_API_KEY=scanner-dev-key
```

Si tu password tiene caracteres especiales (ej. `@` o `:`), usa URL-encoding.

### Probar en Swagger UI (/docs)

En el botón **Authorize**:
- Para endpoints de admin (JWT): usa el flujo OAuth2 Password.
	- `username`: el valor de `ADMIN_USERNAME` (default `admin`)
	- `password`: el valor de `ADMIN_PASSWORD` (default `admin`)
	- `client_id` / `client_secret`: **déjalos vacíos** (no se usan en este MVP)
- Para endpoints del scanner (API Key): usa el header `X-Scanner-Key` con el valor de `SCANNER_API_KEY`.

Run:
```bash
uvicorn app.main:app --reload --port 8000
```
