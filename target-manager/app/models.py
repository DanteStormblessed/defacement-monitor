from __future__ import annotations

import datetime as dt

from sqlalchemy import String, DateTime, Integer, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(2000), unique=True, index=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    scan_interval_seconds: Mapped[int] = mapped_column(Integer, default=1800)

    last_scanned_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: dt.datetime.now(dt.timezone.utc),
        onupdate=lambda: dt.datetime.now(dt.timezone.utc),
    )

    scan_results: Mapped[list["ScanResult"]] = relationship(back_populates="target")


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    target_id: Mapped[int] = mapped_column(Integer, ForeignKey("targets.id"), index=True)

    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))

    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    content_hash: Mapped[str] = mapped_column(String(64))
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    changed: Mapped[bool] = mapped_column(Boolean, default=False)
    similarity: Mapped[int | None] = mapped_column(Integer, nullable=True)  # percent 0-100
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=lambda: dt.datetime.now(dt.timezone.utc))

    target: Mapped[Target] = relationship(back_populates="scan_results")
