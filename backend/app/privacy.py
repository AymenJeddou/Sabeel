"""Privacy step applied to every photo before it is stored (Law 2004-63, NFR-7).

1. Re-encodes the image: this drops all EXIF metadata, including the phone's
   GPS tag, model and timestamp.
2. Blurs faces and licence plates found by OpenCV's bundled Haar cascades
   (frontal faces, profile faces, plates).
3. Downscales to at most 1600 px on the long side (smaller storage, same evidence).

Known limit: Haar cascades miss small, angled or partly hidden faces and
plates. It is a best-effort filter, not a guarantee; the dashboard never shows
photos publicly, and the public endpoints never return photos at all.
"""
from __future__ import annotations

import cv2
import numpy as np

MAX_SIDE = 1600
_CASCADES = ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml", "haarcascade_russian_plate_number.xml")
_classifiers: list[cv2.CascadeClassifier] | None = None


def _get_classifiers() -> list[cv2.CascadeClassifier]:
    global _classifiers
    if _classifiers is None:
        _classifiers = [cv2.CascadeClassifier(cv2.data.haarcascades + name) for name in _CASCADES]
    return _classifiers


def sniff_image_type(data: bytes) -> str | None:
    """'jpeg' | 'png' from the magic bytes, never from the client's filename."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    return None


def find_sensitive_regions(img: np.ndarray) -> list[tuple[int, int, int, int]]:
    gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    min_side = max(24, min(img.shape[:2]) // 40)
    regions: list[tuple[int, int, int, int]] = []
    for clf in _get_classifiers():
        found = clf.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(min_side, min_side))
        regions += [tuple(int(v) for v in r) for r in found]
    return regions


def anonymize(data: bytes, blur: bool = True) -> tuple[bytes, int]:
    """Returns (clean JPEG bytes, number of regions blurred). Raises ValueError
    if the bytes are not a decodable image."""
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("not a decodable image")
    h, w = img.shape[:2]
    if max(h, w) > MAX_SIDE:
        scale = MAX_SIDE / max(h, w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    regions = find_sensitive_regions(img) if blur else []
    for x, y, rw, rh in regions:
        pad = int(0.15 * max(rw, rh))
        x0, y0 = max(x - pad, 0), max(y - pad, 0)
        x1, y1 = min(x + rw + pad, img.shape[1]), min(y + rh + pad, img.shape[0])
        k = max(31, (max(x1 - x0, y1 - y0) // 3) | 1)
        img[y0:y1, x0:x1] = cv2.GaussianBlur(img[y0:y1, x0:x1], (k, k), 0)
    ok, out = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not ok:
        raise ValueError("could not encode image")
    return out.tobytes(), len(regions)
