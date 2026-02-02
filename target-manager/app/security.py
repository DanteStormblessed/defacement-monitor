from __future__ import annotations

import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import jwt, JWTError


SCANNER_API_KEY_HEADER = APIKeyHeader(name="X-Scanner-Key", auto_error=False)

OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def _get_env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def verify_scanner_api_key(api_key: str | None = Security(SCANNER_API_KEY_HEADER)) -> None:
    expected = _get_env_required("SCANNER_API_KEY")
    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid scanner API key")


def _jwt_secret() -> str:
    return _get_env_required("JWT_SECRET")


def create_access_token(subject: str, expires_minutes: int = 60) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(time.time()),
        "exp": now + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=os.getenv("JWT_ALG", "HS256"))


def get_current_admin(token: str = Depends(OAUTH2_SCHEME)) -> str:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[os.getenv("JWT_ALG", "HS256")])
        subject = payload.get("sub")
        if not subject:
            raise HTTPException(status_code=401, detail="Invalid token")
        return subject
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def verify_admin_credentials(username: str, password: str) -> bool:
    # MVP: credenciales por env vars.
    # Futuro: tabla users + hashing.
    expected_user = os.getenv("ADMIN_USERNAME", "admin")
    expected_pass = os.getenv("ADMIN_PASSWORD", "admin")
    return secrets.compare_digest(username, expected_user) and secrets.compare_digest(password, expected_pass)
