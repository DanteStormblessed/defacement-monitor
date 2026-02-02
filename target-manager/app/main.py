from __future__ import annotations

import datetime as dt
import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from .db import Base, engine, get_db, DATABASE_URL
from .models import Target, ScanResult
from .schemas import (
    TokenRequest,
    TokenResponse,
    TargetCreate,
    TargetOut,
    PendingScanTarget,
    ScanResultIn,
    ScanResultOut,
)
from .security import (
    create_access_token,
    get_current_admin,
    verify_admin_credentials,
    verify_scanner_api_key,
)
from .diff_engine import detect_change

logger = logging.getLogger(__name__)

app = FastAPI(title="Defacement Monitor - Target Manager", version="0.1.0")


@app.on_event("startup")
def _startup_init_db() -> None:
    # Avoid failing at import-time (important for uvicorn --reload).
    # Log DB URL with password masked to help diagnose env issues.
    try:
        logger.info("Using DATABASE_URL=%s", make_url(DATABASE_URL).render_as_string(hide_password=True))
    except Exception:
        logger.info("Using DATABASE_URL=(unparseable)")

    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError:
        logger.exception("Database connection failed during startup")
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/")
def root():
    # Useful for load balancer/ingress probes and quick manual checks.
    return {"ok": True, "service": "target-manager", "docs": "/docs"}


@app.post("/api/v1/auth/token", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # This matches the OAuth2 "password" flow used by Swagger UI's Authorize dialog.
    if not verify_admin_credentials(form_data.username, form_data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=form_data.username)
    return TokenResponse(access_token=token)


@app.post("/api/v1/auth/token-json", response_model=TokenResponse, include_in_schema=True)
def login_json(payload: TokenRequest):
    # Convenience endpoint for clients that want JSON instead of x-www-form-urlencoded.
    if not verify_admin_credentials(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=payload.username)
    return TokenResponse(access_token=token)


@app.post("/api/v1/targets", response_model=TargetOut)
def create_target(
    target: TargetCreate,
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    existing = db.query(Target).filter(Target.url == str(target.url)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Target already exists")

    row = Target(
        name=target.name,
        url=str(target.url),
        enabled=target.enabled,
        scan_interval_seconds=target.scan_interval_seconds,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.get("/api/v1/targets", response_model=list[TargetOut])
def list_targets(
    db: Session = Depends(get_db),
    _admin: str = Depends(get_current_admin),
):
    return db.query(Target).order_by(Target.id.asc()).all()


@app.get("/api/v1/targets/pending-scan", response_model=list[PendingScanTarget])
def pending_scan(
    db: Session = Depends(get_db),
    _auth: None = Depends(verify_scanner_api_key),
    limit: int = 25,
):
    now = dt.datetime.now(dt.timezone.utc)

    candidates: list[Target] = (
        db.query(Target)
        .filter(Target.enabled == True)  # noqa: E712
        .order_by(Target.id.asc())
        .all()
    )

    due: list[Target] = []
    for t in candidates:
        if t.last_scanned_at is None:
            due.append(t)
            continue
        next_due = t.last_scanned_at + dt.timedelta(seconds=int(t.scan_interval_seconds))
        if next_due <= now:
            due.append(t)

    return [PendingScanTarget(id=t.id, url=t.url) for t in due[: max(1, min(limit, 200))]]


@app.post("/api/v1/scan-results", response_model=ScanResultOut)
def submit_scan_result(
    payload: ScanResultIn,
    db: Session = Depends(get_db),
    _auth: None = Depends(verify_scanner_api_key),
):
    target = db.query(Target).filter(Target.id == payload.target_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    fetched_at = payload.fetched_at or dt.datetime.now(dt.timezone.utc)

    verdict = detect_change(
        prev_text=target.last_text,
        new_text=payload.content_text,
        prev_hash=target.last_hash,
        new_hash=payload.content_hash,
    )

    scan = ScanResult(
        target_id=target.id,
        fetched_at=fetched_at,
        http_status=payload.http_status,
        final_url=payload.final_url,
        content_hash=payload.content_hash,
        content_text=payload.content_text,
        changed=verdict.changed,
        similarity=verdict.similarity_percent,
        notes=verdict.notes,
    )

    # Update target baseline
    target.last_scanned_at = fetched_at
    if target.last_hash is None:
        # first time baseline
        target.last_hash = payload.content_hash
        target.last_text = payload.content_text
    else:
        # update baseline after every scan (MVP). Futuro: solo si "no changed" o según políticas.
        target.last_hash = payload.content_hash
        target.last_text = payload.content_text

    db.add(scan)
    db.add(target)
    db.commit()
    db.refresh(scan)

    return scan
