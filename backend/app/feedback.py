"""Model feedback loop (issue #28, part A).

Every human decision about a pothole becomes a training label:
- an officer clicks "Pas un nid-de-poule" or two citizens tap it -> `not_pothole`
- an officer approves a work sheet -> `confirmed_pothole`

Each label keeps the photo (already face/plate-blurred and EXIF-stripped at
intake, see privacy.py) plus what the model predicted, so
`ml-training/export_feedback_dataset.py` can turn the table into a YOLO dataset.
Photos with a label are exempt from the delete-after-approval rule.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db_models import FeedbackLabel, Pothole, Report


async def label_pothole(
    db: AsyncSession, p: Pothole, label: str, source: str, note: str | None = None, only_best: bool = False
) -> int:
    """Labels the pothole's reports that still have a photo (or only the most
    confident one with `only_best`). Idempotent."""
    reports = list(
        (await db.execute(select(Report).where(Report.pothole_id == p.pothole_id, Report.photo_url.is_not(None)))).scalars()
    )
    if only_best and reports:
        reports = [max(reports, key=lambda r: r.confidence or 0)]
    n = 0
    for r in reports:
        result = await db.execute(
            insert(FeedbackLabel)
            .values(
                report_id=r.report_id,
                pothole_id=p.pothole_id,
                label=label,
                source=source,
                photo_path=r.photo_url,
                model_score=r.score,
                model_confidence=r.confidence,
                boxes=r.boxes,
                note=note,
            )
            .on_conflict_do_nothing(index_elements=["report_id", "label"])
        )
        n += result.rowcount or 0
    return n


async def false_positive_rate(db: AsyncSession) -> float | None:
    """not_pothole labels / all labelled potholes (exposed in analytics)."""
    rows = dict(
        (await db.execute(select(FeedbackLabel.label, func.count(func.distinct(FeedbackLabel.pothole_id))).group_by(FeedbackLabel.label))).all()
    )
    total = sum(rows.values())
    return round(rows.get("not_pothole", 0) / total, 3) if total else None
