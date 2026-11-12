"""Work-order PDF: officer and rule text can't break the ReportLab markup."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from backend.app import pdf


def test_pdf_renders_markup_characters_and_a_working_map_link():
    now = datetime(2026, 11, 12, 9, 0, tzinfo=timezone.utc)
    p = SimpleNamespace(
        pothole_id=uuid.uuid4(), ref="SBL-0001", lat=36.8, lon=10.18, severity=4,
        address_label="Rue <Ibn Khaldoun> & Co", road_ref="RN8", road_name=None, road_type="urbain_principal",
        report_count=3, device_count=2, confirmed_at=now, sla_due_at=now,
        sheet_generated_at=now, sheet_approved_at=now, sheet_approved_by="Ali & <Fils>",
        sheet_text="**Travaux** : purge & reprise\n- balisage < 1 h",
        sheet_citations=[{"rule_id": "L86-17<art.3>", "source": "Loi 86-17 & décret", "excerpt": "a < b & c"}],
        sheet_hash="ab" * 32,
    )
    data = pdf.render_sheet_pdf(p, None)
    assert data.startswith(b"%PDF") and len(data) > 2000
    assert pdf._x('?mlat=1&mlon=2') == "?mlat=1&amp;mlon=2"
