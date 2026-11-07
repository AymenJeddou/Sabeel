"""
Severity scoring rule (1-5): turns the model's boxes into the `score` field
consumed by the Core API, the SLA policy and the RAG work sheet.

v2 (issue #42). Severity is a 2-D proxy: the relative area of the largest
confident box. Depth cannot be measured from one photo. Two changes from v1:

1. **Separate bands per capture mode.** A citizen standing over a pothole
   (`manual`, `web`) fills much more of the frame than a dashcam
   (`driving_mode`) sees from 10 m away. With one set of bands, 71 % of the
   close-up seed photos scored 5. The dashcam bands are the v1 bands, which
   fit RDD2022's dashcam views.
2. **No +1 for high confidence.** Confidence says how sure the model is that
   it is a pothole, not how bad the pothole is.

| Box area / image area | manual & web (close-up) | driving_mode (dashcam) |
|-----------------------|-------------------------|------------------------|
| score 1               | < 3 %                   | < 0.5 %                |
| score 2               | < 8 %                   | < 1.5 %                |
| score 3               | < 20 %                  | < 4 %                  |
| score 4               | < 35 %                  | < 8 %                  |
| score 5               | ≥ 35 %                  | ≥ 8 %                  |

The close-up bands were set on the 24 detected seed photos so that the
scores spread over all five levels (3 / 5 / 6 / 6 / 4 instead of
1 / 1 / 2 / 3 / 17). They are provisional: re-fit them on the human-labelled
severity set described in #42 once it exists (ml-training/eval/README.md).
"""

from typing import Any, Dict, List

BANDS = {
    "close_up": (0.03, 0.08, 0.20, 0.35),
    "dashcam": (0.005, 0.015, 0.04, 0.08),
}
MODE_FOR_SOURCE = {"manual": "close_up", "web": "close_up", "driving_mode": "dashcam"}


def score_from_detections(
    boxes: List[Dict[str, Any]],
    image_width: int,
    image_height: int,
    conf_threshold: float = 0.25,
    source: str = "manual",
) -> int:
    """Returns an integer score 1-5, or 0 if there is no confident box.

    boxes: dicts with keys x, y, w, h, conf. source: the report's capture mode.
    """
    valid = [b for b in boxes if b.get("conf", 0) >= conf_threshold]
    if not valid:
        return 0
    rel = max(b["w"] * b["h"] for b in valid) / float(image_width * image_height)
    bands = BANDS[MODE_FOR_SOURCE.get(source, "close_up")]
    return 1 + sum(rel >= t for t in bands)


if __name__ == "__main__":
    # Self-check: the band edges and the per-mode difference.
    box = lambda area: [{"x": 0, "y": 0, "w": int(area * 100), "h": 100, "conf": 0.9}]
    assert score_from_detections([], 100, 100) == 0
    assert score_from_detections(box(0.02), 100, 100, source="manual") == 1
    assert score_from_detections(box(0.02), 100, 100, source="driving_mode") == 3
    assert score_from_detections(box(0.50), 100, 100, source="web") == 5
    assert score_from_detections(box(0.10), 100, 100, source="manual") == 3
    print("severity_scoring self-check passed")
