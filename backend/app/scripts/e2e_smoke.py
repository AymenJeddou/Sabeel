"""End-to-end smoke test against a running stack (issue #14), the demo path
of the roadmap: two phones report the same pothole -> confirmed -> enriched
and routed -> sheet generated -> officer approves -> citizen sees "Transmis"
-> officer marks fixed with proof -> public counters update.

    python -m backend.app.scripts.e2e_smoke                         # http://127.0.0.1:8000
    python -m backend.app.scripts.e2e_smoke --api https://... --token <office token> --internal <INTERNAL_TOKEN>

Uses a random spot so it never merges into existing data, and real seed
photos (the model must find the pothole). Exits non-zero on the first failure.
"""
from __future__ import annotations

import argparse
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

SEED = Path(__file__).resolve().parents[1] / "static" / "photos" / "_seed"


def step(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {name}{' · ' + detail if detail else ''}")
    if not ok:
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--api", default="http://127.0.0.1:8000")
    ap.add_argument("--token", default="demo-ministry", help="an office token that can see the spot (ministry)")
    ap.add_argument("--internal", default="", help="INTERNAL_TOKEN, to run jobs when the API has no job loop")
    a = ap.parse_args()
    api = httpx.Client(base_url=a.api, timeout=60)
    officer = {"Authorization": f"Bearer {a.token}"}
    lat, lon = 36.80 + random.uniform(-0.02, 0.02), 10.18 + random.uniform(-0.02, 0.02)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    step("health", api.get("/health").status_code == 200)

    t0 = time.perf_counter()
    reports = []
    for phone in ("e2e-phone-a", "e2e-phone-b"):
        form = {"device_report_id": f"e2e-{uuid.uuid4()}", "device_id": f"{phone}-{uuid.uuid4().hex[:6]}",
                "lat": f"{lat:.6f}", "lon": f"{lon:.6f}", "gps_accuracy_m": "4", "speed_kmh": "0",
                "direction_deg": "90", "captured_at": now, "source": "manual"}
        r = api.post("/reports", data=form, files={"photo": ("p.jpg", (SEED / "p08.jpg").read_bytes(), "image/jpeg")})
        reports.append((form, r.json() if r.status_code < 300 else {}))
        step(f"report from {phone}", r.status_code == 201 and r.json().get("detected"), f"{r.status_code}")
    elapsed = time.perf_counter() - t0
    body = reports[-1][1]
    step("two phones confirm one pothole", body["status"] == "confirmed" and body["pothole_id"] == reports[0][1]["pothole_id"])
    step("report round trip < 3 s", elapsed / 2 < 3, f"{elapsed / 2:.2f} s per report")
    pid = body["pothole_id"]

    sheet = {}
    for _ in range(40):  # background jobs: enrichment then RAG sheet
        if a.internal:
            api.post("/internal/jobs/run", headers={"X-Internal-Token": a.internal})
        sheet = api.get(f"/potholes/{pid}/sheet", headers=officer).json()
        if sheet.get("sheet_status") in ("generated", "failed"):
            break
        time.sleep(3)
    step("work sheet generated", sheet.get("sheet_status") == "generated", f"citations {[c['rule_id'] for c in sheet.get('sheet_citations', [])]}")

    detail = api.get(f"/potholes/{pid}", headers=officer).json()
    step("routed to an office", bool(detail.get("target_office")), str(detail.get("target_office")))

    r = api.post(f"/potholes/{pid}/sheet/approve", headers=officer)
    step("officer approves the sheet", r.status_code == 200, r.text[:120])
    track = api.get(f"/reports/{reports[0][0]['device_report_id']}").json()
    step("citizen tracker shows 'sheet_sent'", track["status"] == "sheet_sent")

    pdf = api.get(f"/potholes/{pid}/sheet.pdf", headers=officer)
    step("PDF work order", pdf.content[:5] == b"%PDF-", f"{len(pdf.content) // 1024} KB")
    fp = r.json()["fingerprint"]
    step("QR fingerprint verifies", api.get(f"/public/potholes/{pid}/verify", params={"h": fp}).json()["valid"])

    proof = (SEED / "fp_crack.jpg").read_bytes()  # a road with no pothole
    r = api.post(f"/potholes/{pid}/fix", headers=officer, data={"note": "enrobé à chaud, compactage"},
                 files={"proof": ("proof.jpg", proof, "image/jpeg")})
    step("marked fixed with proof, AI check passed", r.status_code == 200 and r.json()["fix_verified"], r.text[:120])
    step("citizen tracker shows 'fixed'", api.get(f"/reports/{reports[0][0]['device_report_id']}").json()["status"] == "fixed")
    step("public stats answer", api.get("/public/stats").status_code == 200)
    print(f"\nAll steps passed (pothole {detail['ref']}).")


if __name__ == "__main__":
    main()
