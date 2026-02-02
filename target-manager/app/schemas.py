from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, HttpUrl, Field


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TargetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    url: HttpUrl
    scan_interval_seconds: int = Field(default=1800, ge=60, le=24 * 60 * 60)
    enabled: bool = True


class TargetOut(BaseModel):
    id: int
    name: str
    url: str
    enabled: bool
    scan_interval_seconds: int
    last_scanned_at: dt.datetime | None
    last_hash: str | None

    class Config:
        from_attributes = True


class PendingScanTarget(BaseModel):
    id: int
    url: str

    class Config:
        from_attributes = True


class ScanResultIn(BaseModel):
    target_id: int
    fetched_at: dt.datetime | None = None

    http_status: int | None = None
    final_url: str | None = None

    content_hash: str
    content_text: str | None = None


class ScanResultOut(BaseModel):
    id: int
    target_id: int
    fetched_at: dt.datetime
    changed: bool
    similarity: int | None
    notes: str | None

    class Config:
        from_attributes = True
