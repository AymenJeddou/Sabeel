"""
Official Severity Scoring Rule (1–5) – WP1 Sprint 1
This is the function that produces the `score` field consumed by WP2 and WP3.
Treat as frozen unless the whole team agrees to change it.
"""

from typing import List, Dict, Any


def score_from_detections(
    boxes: List[Dict[str, Any]],
    image_width: int,
    image_height: int,
    conf_threshold: float = 0.25,
) -> int:
    """
    Returns integer score 1–5 (or 0 if no valid detections).

    boxes: list of dicts with keys: x, y, w, h, conf (and optionally class)
    """
    if not boxes:
        return 0

    # Keep only confident detections
    valid = [b for b in boxes if b.get("conf", 0) >= conf_threshold]
    if not valid:
        return 0

    img_area = float(image_width * image_height)
    max_rel_area = 0.0
    max_conf = 0.0

    for b in valid:
        area = b["w"] * b["h"]
        rel = area / img_area
        if rel > max_rel_area:
            max_rel_area = rel
            max_conf = b.get("conf", 0.5)

    # Heuristic based on relative area (2-D proxy for size/severity)
    if max_rel_area < 0.005:
        base = 1
    elif max_rel_area < 0.015:
        base = 2
    elif max_rel_area < 0.04:
        base = 3
    elif max_rel_area < 0.08:
        base = 4
    else:
        base = 5

    # Small boost for very high confidence
    if max_conf > 0.85 and base < 5:
        base += 1

    return min(5, max(1, base))