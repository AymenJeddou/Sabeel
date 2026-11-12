"""Local photo storage never reads or deletes outside its folders."""
import asyncio

from backend.app import storage


def test_local_paths_stay_inside_their_root():
    assert storage._local("/static/photos/ab/c.jpg", storage.PHOTOS_DIR) == (storage.PHOTOS_DIR / "ab/c.jpg").resolve()
    assert storage._local("/static/photos/../../config.py", storage.PHOTOS_DIR) is None
    assert storage._local("/static/../app/config.py", storage.STATIC_DIR) is None


def test_read_and_delete_refuse_traversal():
    victim = storage.STATIC_DIR.parent / "config.py"
    assert victim.exists()
    assert asyncio.run(storage.read("/static/../config.py")) is None
    asyncio.run(storage.delete("/static/photos/../../config.py"))
    assert victim.exists()


def test_read_never_fetches_foreign_urls():
    assert asyncio.run(storage.read("http://169.254.169.254/latest/meta-data/")) is None


def test_csv_export_cells_cannot_run_formulas():
    from backend.app.routers.authorities import csv_safe

    assert csv_safe('=HYPERLINK("http://evil","Route")') == '\'=HYPERLINK("http://evil","Route")'
    assert csv_safe("@SUM(A1)") == "'@SUM(A1)" and csv_safe("-1+2") == "'-1+2"
    assert csv_safe("Route de Bizerte") == "Route de Bizerte"
    assert csv_safe(-10.5) == -10.5 and csv_safe(None) is None
