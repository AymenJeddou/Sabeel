"""Officer CSV export: cells from OpenStreetMap can't run as spreadsheet formulas."""

def test_csv_export_cells_cannot_run_formulas():
    from backend.app.routers.authorities import csv_safe

    assert csv_safe('=HYPERLINK("http://evil","Route")') == '\'=HYPERLINK("http://evil","Route")'
    assert csv_safe("@SUM(A1)") == "'@SUM(A1)" and csv_safe("-1+2") == "'-1+2"
    assert csv_safe("Route de Bizerte") == "Route de Bizerte"
    assert csv_safe(-10.5) == -10.5 and csv_safe(None) is None
