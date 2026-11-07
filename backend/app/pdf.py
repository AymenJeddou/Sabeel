"""Work-order PDF (issue #25) with a tamper-evident footer.

When an officer approves a sheet, `sheet_fingerprint()` hashes the pothole id,
the approved text, the cited rule ids, the approval time and the office. The
PDF prints the first 16 hex characters and a QR code pointing to the public
verification page (`/#/verify/<pothole_id>?h=<fingerprint>`): anyone holding
the paper can scan it and see whether it matches what was approved in Sabeel.
"""
from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.app.config import settings
from backend.app.db_models import Office, Pothole

BRAND = colors.HexColor("#0F6E6A")
SEVERITY_FR = {1: "1 · faible", 2: "2 · faible", 3: "3 · moyenne", 4: "4 · élevée", 5: "5 · dangereuse"}


def sheet_fingerprint(p: Pothole, office_code: str | None) -> str:
    payload = {
        "pothole_id": str(p.pothole_id),
        "sheet_text": p.sheet_text or "",
        "citations": [c.get("rule_id") for c in (p.sheet_citations or [])],
        "approved_at": p.sheet_approved_at.isoformat() if p.sheet_approved_at else None,
        "office": office_code,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def verify_url(p: Pothole) -> str:
    return f"{settings.public_base_url}/#/verify/{p.pothole_id}?h={(p.sheet_hash or '')[:16]}"


def _qr(url: str, size: float = 30 * mm) -> Drawing:
    widget = QrCodeWidget(url)
    x0, y0, x1, y1 = widget.getBounds()
    d = Drawing(size, size, transform=[size / (x1 - x0), 0, 0, size / (y1 - y0), 0, 0])
    d.add(widget)
    return d


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%d/%m/%Y %H:%M UTC") if dt else "—"


def render_sheet_pdf(p: Pothole, office: Office | None) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=f"Fiche de travaux {p.ref}", author="Sabeel")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=BRAND, alignment=0, fontSize=18, spaceAfter=2)
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8, textColor=colors.HexColor("#555555"))
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=10, leading=14)
    h2 = ParagraphStyle("h2", parent=ss["Heading3"], textColor=BRAND, spaceBefore=10)

    osm = f"https://www.openstreetmap.org/?mlat={p.lat:.6f}&mlon={p.lon:.6f}#map=19/{p.lat:.6f}/{p.lon:.6f}"
    facts = [
        ["Référence", p.ref, "Sévérité", SEVERITY_FR.get(p.severity or 0, "—")],
        ["Adresse", p.address_label or "—", "Route", " ".join(x for x in (p.road_ref, p.road_name) if x) or "—"],
        ["Position", f"{p.lat:.6f}, {p.lon:.6f}", "Type", p.road_type or "—"],
        ["Bureau", office.name if office else "—", "Signalements", f"{p.report_count} ({p.device_count} citoyens)"],
        ["Confirmé le", _fmt(p.confirmed_at), "Échéance", _fmt(p.sla_due_at)],
    ]
    table = Table(facts, colWidths=[24 * mm, 62 * mm, 24 * mm, 64 * mm])
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 9),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND),
        ("TEXTCOLOR", (2, 0), (2, -1), BRAND),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    story = [
        Paragraph("Fiche de travaux · Sabeel", h1),
        Paragraph(f"Généré le {_fmt(p.sheet_generated_at)} · approuvé le {_fmt(p.sheet_approved_at)}"
                  f" par {p.sheet_approved_by or '—'}", small),
        Spacer(1, 6 * mm),
        table,
        Paragraph(f'Carte : <a href="{osm}" color="#0F6E6A">{osm}</a>', small),
        Paragraph("Fiche", h2),
    ]
    import re

    for line in (p.sheet_text or "").strip().splitlines():
        safe = line.replace("&", "&amp;").replace("<", "&lt;")
        safe = re.sub(r"^\s*[*-]\s+", "• ", safe)
        safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)  # LLM markdown bold
        story.append(Paragraph(safe or "&nbsp;", body))
    story.append(Paragraph("Textes cités", h2))
    for c in p.sheet_citations or []:
        story.append(Paragraph(f"<b>{c.get('rule_id')}</b> · {c.get('source', '')}", body))
        if c.get("excerpt"):
            story.append(Paragraph(f"<i>« {c['excerpt'].replace('<', '&lt;')}… »</i>", small))
    if not p.sheet_citations:
        story.append(Paragraph("Aucune citation.", small))

    story += [Spacer(1, 8 * mm)]
    fp = (p.sheet_hash or "")[:16] or "non approuvée"
    footer = Table(
        [[_qr(verify_url(p)), Paragraph(
            f"<b>Empreinte : {fp}</b><br/>Scannez le code pour vérifier que cette fiche correspond à la version "
            f"approuvée dans Sabeel.<br/>{verify_url(p)}", small)]],
        colWidths=[34 * mm, 140 * mm],
    )
    footer.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story.append(footer)
    doc.build(story)
    return buf.getvalue()

