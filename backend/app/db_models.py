"""SQLAlchemy models mirroring backend/app/db/schema.sql. Not yet wired into the
Sprint 1 stub endpoints (see README) — ready for Sprint 2 when endpoints read/write real data.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Enum as SAEnum, Float, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db import Base
from backend.app.schemas import ReportSource
from backend.app.status import ReportStatus


class Report(Base):
    __tablename__ = "reports"

    report_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_report_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    direction_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(nullable=False)
    source: Mapped[ReportSource] = mapped_column(SAEnum(ReportSource, name="report_source"), nullable=False)
    score: Mapped[int | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        SAEnum(ReportStatus, name="report_status"), nullable=False, default=ReportStatus.NEW
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    sheet_text: Mapped[str | None] = mapped_column(String, nullable=True)
    target_office: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint("score IS NULL OR (score BETWEEN 1 AND 5)", name="score_range"),
        CheckConstraint("confidence IS NULL OR (confidence BETWEEN 0 AND 1)", name="confidence_range"),
    )
