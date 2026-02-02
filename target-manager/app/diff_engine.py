from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from difflib import SequenceMatcher


_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class DiffVerdict:
    changed: bool
    similarity_percent: int | None
    notes: str | None


def normalize_text(text: str) -> str:
    text = text.strip()
    text = _WS_RE.sub(" ", text)
    return text


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def detect_change(prev_text: str | None, new_text: str | None, prev_hash: str | None, new_hash: str) -> DiffVerdict:
    # Si no hay texto, solo podemos comparar hashes
    if not prev_hash:
        return DiffVerdict(changed=False, similarity_percent=None, notes="baseline_created")

    if prev_hash == new_hash:
        return DiffVerdict(changed=False, similarity_percent=100, notes="hash_equal")

    if prev_text is None or new_text is None:
        return DiffVerdict(changed=True, similarity_percent=None, notes="hash_changed_no_text")

    a = normalize_text(prev_text)
    b = normalize_text(new_text)

    if not a or not b:
        return DiffVerdict(changed=True, similarity_percent=None, notes="empty_text")

    ratio = SequenceMatcher(a=a, b=b).ratio()
    similarity = int(round(ratio * 100))

    # Heurística MVP: si cambió el hash, se marca como cambio.
    # Se usa similarity para priorizar alertas (cambios grandes vs sutiles).
    notes = "hash_changed"
    if similarity >= 98:
        notes = "subtle_change"  # pequeño cambio, potencial defacement sutil

    return DiffVerdict(changed=True, similarity_percent=similarity, notes=notes)
