from __future__ import annotations

import hashlib
import os
import random
import sys
import time
from dataclasses import dataclass
from typing import Any

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class Target:
    id: int
    url: str


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Remove common non-content
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(" ")
    text = " ".join(text.split())
    return text


def get_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env var: {name}")
    return v


def api_headers() -> dict[str, str]:
    return {"X-Scanner-Key": get_env("SCANNER_API_KEY")}


def fetch_pending_targets(base_url: str) -> list[Target]:
    url = f"{base_url.rstrip('/')}/api/v1/targets/pending-scan"
    r = requests.get(url, headers=api_headers(), timeout=20)
    r.raise_for_status()

    out: list[Target] = []
    for row in r.json():
        out.append(Target(id=int(row["id"]), url=str(row["url"])))
    return out


def post_scan_result(base_url: str, body: dict[str, Any]) -> None:
    url = f"{base_url.rstrip('/')}/api/v1/scan-results"
    r = requests.post(url, json=body, headers=api_headers(), timeout=30)
    r.raise_for_status()


def fetch_html_with_requests(target_url: str) -> tuple[str, int | None, str | None]:
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    ]

    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    r = requests.get(target_url, headers=headers, timeout=30, allow_redirects=True)
    return r.text, r.status_code, r.url


def fetch_html_with_seleniumbase(target_url: str) -> tuple[str, int | None, str | None]:
    # SeleniumBase is optional at runtime; if it fails we fallback to requests.
    try:
        from seleniumbase import SB

        with SB(uc=True, headless=True) as sb:
            sb.open(target_url)
            sb.wait(2)
            html = sb.get_page_source()
            return html, None, sb.get_current_url()
    except Exception:
        raise


def main() -> int:
    base_url = get_env("TARGET_MANAGER_URL")

    try_selenium = os.getenv("USE_SELENIUM", "1") == "1"

    targets = fetch_pending_targets(base_url)
    if not targets:
        print("No pending targets.")
        return 0

    for t in targets:
        # Polite delay to avoid hammering sites
        time.sleep(float(os.getenv("SCAN_DELAY_SECONDS", "1.0")))

        try:
            if try_selenium:
                html, http_status, final_url = fetch_html_with_seleniumbase(t.url)
            else:
                html, http_status, final_url = fetch_html_with_requests(t.url)
        except Exception as exc:
            print(f"Failed to fetch {t.url}: {exc}")
            continue

        text = extract_visible_text(html)
        content_hash = sha256_hex(text)

        body: dict[str, Any] = {
            "target_id": t.id,
            "content_hash": content_hash,
            "content_text": text,
            "http_status": http_status,
            "final_url": final_url,
        }

        post_scan_result(base_url, body)
        print(f"Reported target_id={t.id} hash={content_hash[:8]}...")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(str(e), file=sys.stderr)
        raise
