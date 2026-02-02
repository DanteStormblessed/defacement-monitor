import os
from datetime import datetime, timezone

from fastapi.testclient import TestClient

# Configure minimal env for app import
os.environ.setdefault("JWT_SECRET", "dev-secret")
os.environ.setdefault("SCANNER_API_KEY", "scanner-dev-key")

from app.main import app  # noqa: E402


def sha256_hex(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    client = TestClient(app)

    # 1) Admin login
    token_resp = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "admin"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert token_resp.status_code == 200, token_resp.text
    token = token_resp.json()["access_token"]

    # 2) Create target
    target_resp = client.post(
        "/api/v1/targets",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Example", "url": "https://example.org", "scan_interval_seconds": 1800},
    )
    assert target_resp.status_code in (200, 409), target_resp.text

    # 3) Pending scan (scanner)
    pending = client.get(
        "/api/v1/targets/pending-scan", headers={"X-Scanner-Key": "scanner-dev-key"}
    )
    assert pending.status_code == 200, pending.text

    if not pending.json():
        print("No pending targets (ok if recently scanned).")
        return

    target_id = pending.json()[0]["id"]

    # 4) Submit scan-result
    text = "Hello world"
    scan = client.post(
        "/api/v1/scan-results",
        headers={"X-Scanner-Key": "scanner-dev-key"},
        json={
            "target_id": target_id,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": sha256_hex(text),
            "content_text": text,
            "http_status": 200,
            "final_url": "https://example.org",
        },
    )
    assert scan.status_code == 200, scan.text
    print("Smoke OK:", scan.json())


if __name__ == "__main__":
    main()
