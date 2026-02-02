# Scanner

Bot ejecutable localmente o desde GitHub Actions.

## Variables de entorno
- `TARGET_MANAGER_URL` (ej. `https://mi-api.com` o `http://localhost:8000`)
- `SCANNER_API_KEY` (API Key del bot)
- `USE_SELENIUM` ("1"/"0")
- `SCAN_DELAY_SECONDS` (delay entre targets)

## Nota
SeleniumBase puede requerir dependencias adicionales en Linux runner; si falla, puedes poner `USE_SELENIUM=0` para fallback con `requests`.
