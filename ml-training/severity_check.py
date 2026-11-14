"""Compares the severity rule with human severity labels (issue #42, step 2).

    python severity_check.py                       # eval/severity_labels.csv, photos in eval/severity_photos/
    python severity_check.py --labels my.csv --photos folder

The CSV has one row per photo with `human_severity_final` (1-5, agreed by two
raters with the rubric in eval/README.md) and `source` (manual | driving_mode).
Prints the confusion matrix (rows = human, columns = model), the exact and
±1 agreement, and the share of 5s, then refits the close-up area bands that
would best match the human labels (to discuss before changing
severity_scoring.py: the score feeds deadlines, sheets and priority).
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import inference
from severity_scoring import BANDS


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", type=Path, default=Path("eval/severity_labels.csv"))
    ap.add_argument("--photos", type=Path, default=Path("eval/severity_photos"))
    a = ap.parse_args()

    rows = [r for r in csv.DictReader(a.labels.open(encoding="utf-8")) if r.get("human_severity_final")]
    if not rows:
        raise SystemExit(f"No labelled rows in {a.labels} yet: see eval/README.md for the protocol.")

    matrix = [[0] * 6 for _ in range(6)]  # [human][model], 0 = no detection
    areas: list[tuple[float, int]] = []
    for r in rows:
        data = (a.photos / r["image"]).read_bytes()
        res = inference.infer(data, source=r.get("source") or "manual")
        human = int(r["human_severity_final"])
        model = res["score"] or 0
        matrix[human][model] += 1
        if res["boxes"]:
            w, h = res["image_size"]
            biggest = max(b["w"] * b["h"] for b in res["boxes"]) / (w * h)
            areas.append((biggest, human))

    n = len(rows)
    exact = sum(matrix[i][i] for i in range(1, 6))
    near = sum(matrix[i][j] for i in range(1, 6) for j in range(1, 6) if abs(i - j) <= 1)
    print("human \\ model   none    1    2    3    4    5")
    for i in range(1, 6):
        print(f"      {i}       " + "".join(f"{matrix[i][j]:5d}" for j in range(6)))
    print(f"exact agreement {exact}/{n} · within ±1 {near}/{n} · model 5s {sum(matrix[i][5] for i in range(6))}/{n}")

    # Best close-up bands: the thresholds between consecutive human levels,
    # as the midpoint of the median areas of each level.
    by_level = {lvl: sorted(x for x, h in areas if h == lvl) for lvl in range(1, 6)}
    medians = {lvl: v[len(v) // 2] for lvl, v in by_level.items() if v}
    if len(medians) == 5:
        fitted = tuple(round((medians[i] + medians[i + 1]) / 2, 4) for i in range(1, 5))
        print(f"current close-up bands {BANDS['close_up']} -> suggested {fitted}")
    else:
        print("Need detected photos for all five human levels to suggest new bands.")


if __name__ == "__main__":
    main()
