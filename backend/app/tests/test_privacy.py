"""Photo privacy step: type sniffing, downscale, metadata stripped. No database."""
import cv2
import numpy as np
import pytest

from backend.app import privacy


def _jpeg(w, h):
    ok, buf = cv2.imencode(".jpg", np.full((h, w, 3), 128, np.uint8))
    assert ok
    return buf.tobytes()


def test_sniff_by_magic_bytes_only():
    assert privacy.sniff_image_type(_jpeg(8, 8)) == "jpeg"
    assert privacy.sniff_image_type(b"\x89PNG\r\n\x1a\n" + b"0" * 8) == "png"
    assert privacy.sniff_image_type(b"GIF89a") is None
    assert privacy.sniff_image_type(b"") is None


def test_downscales_the_long_side():
    out, _ = privacy.anonymize(_jpeg(4000, 1000), blur=False)
    img = cv2.imdecode(np.frombuffer(out, np.uint8), cv2.IMREAD_COLOR)
    assert img.shape[:2] == (400, privacy.MAX_SIDE)


def test_exif_is_dropped():
    data = _jpeg(64, 64)
    exif = b"\xff\xe1\x00\x16Exif\x00\x00GPS-lat-36.8-lon-10.1"
    tagged = data[:2] + exif + data[2:]
    out, _ = privacy.anonymize(tagged, blur=False)
    assert b"Exif" in tagged and b"Exif" not in out and b"GPS" not in out


def test_garbage_is_rejected():
    with pytest.raises(ValueError):
        privacy.anonymize(b"not an image")
