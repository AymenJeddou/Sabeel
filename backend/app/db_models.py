"""SQLAlchemy models mirroring backend/app/db/migrations/*.sql.

Statuses and sources are plain strings in the database (CHECK constraints);
the Python enums in status.py / schemas.py are their single source of truth.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db import Base


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _ts(nullable: bool = True) -> Mapped[datetime | None]:
    return mapped_column(DateTime(timezone=True), nullable=nullable)


def _created() -> Mapped[datetime]:
    # server_default makes SQLAlchemy omit the column on INSERT instead of sending NULL.
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Office(Base):
    __tablename__ = "offices"

    office_id: Mapped[uuid.UUID] = _uuid_pk()
    code: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)  # Municipality | DGPC | Ministry of Equipment
    region: Mapped[str | None] = mapped_column(String)
    municipality: Mapped[str | None] = mapped_column(String)
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    parent_office_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("offices.office_id"))
    token_hash: Mapped[str | None] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = _created()

    @property
    def is_ministry(self) -> bool:
        return self.kind == "Ministry of Equipment"


class Pothole(Base):
    __tablename__ = "potholes"

    pothole_id: Mapped[uuid.UUID] = _uuid_pk()
    status: Mapped[str] = mapped_column(String, default="new")
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    report_count: Mapped[int] = mapped_column(Integer, default=0)
    device_count: Mapped[int] = mapped_column(Integer, default=0)
    confirm_count: Mapped[int] = mapped_column(Integer, default=0)
    fixed_ok_count: Mapped[int] = mapped_column(Integer, default=0)
    not_fixed_count: Mapped[int] = mapped_column(Integer, default=0)
    not_pothole_count: Mapped[int] = mapped_column(Integer, default=0)
    severity: Mapped[int | None] = mapped_column(SmallInteger)
    max_confidence: Mapped[float | None] = mapped_column(Float)
    priority_score: Mapped[float] = mapped_column(Float, default=0)
    priority_components: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    road_type: Mapped[str | None] = mapped_column(String)
    road_class: Mapped[str | None] = mapped_column(String)
    road_name: Mapped[str | None] = mapped_column(String)
    road_ref: Mapped[str | None] = mapped_column(String)
    region: Mapped[str | None] = mapped_column(String)
    municipality: Mapped[str | None] = mapped_column(String)
    address_label: Mapped[str | None] = mapped_column(String)
    enrichment_source: Mapped[str | None] = mapped_column(String)
    target_office_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("offices.office_id"))

    sheet_status: Mapped[str | None] = mapped_column(String)
    sheet_text: Mapped[str | None] = mapped_column(String)
    sheet_text_original: Mapped[str | None] = mapped_column(String)
    sheet_citations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    sheet_generated_at: Mapped[datetime | None] = _ts()
    sheet_approved_at: Mapped[datetime | None] = _ts()
    sheet_approved_by: Mapped[str | None] = mapped_column(String)
    sheet_hash: Mapped[str | None] = mapped_column(String)

    confirmed_at: Mapped[datetime | None] = _ts()
    sla_due_at: Mapped[datetime | None] = _ts()
    escalated_at: Mapped[datetime | None] = _ts()
    fixed_at: Mapped[datetime | None] = _ts()
    reopened_at: Mapped[datetime | None] = _ts()
    fixed_proof_url: Mapped[str | None] = mapped_column(String)
    fixed_note: Mapped[str | None] = mapped_column(String)
    fix_check: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    fix_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    rain_mm_48h: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _created()

    @property
    def ref(self) -> str:
        """Short code shown to citizens and officers, e.g. TN-3FA9C1."""
        return "TN-" + self.pothole_id.hex[:6].upper()


class Report(Base):
    __tablename__ = "reports"

    report_id: Mapped[uuid.UUID] = _uuid_pk()
    device_report_id: Mapped[str] = mapped_column(String, unique=True)
    pothole_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("potholes.pothole_id"))
    photo_url: Mapped[str | None] = mapped_column(String)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float)
    speed_kmh: Mapped[float | None] = mapped_column(Float)
    direction_deg: Mapped[float | None] = mapped_column(Float)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String)
    score: Mapped[int | None] = mapped_column(SmallInteger)
    confidence: Mapped[float | None] = mapped_column(Float)
    detected: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    boxes: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    inference_ms: Mapped[float | None] = mapped_column(Float)
    # Legacy (Sprint 1 contract): mirrors the pothole's status for old clients.
    status: Mapped[str] = mapped_column(String, default="new")
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))
    sheet_text: Mapped[str | None] = mapped_column(String)
    target_office: Mapped[str | None] = mapped_column(String)
    device_id: Mapped[str | None] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _created()


class ReportEvent(Base):
    __tablename__ = "report_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pothole_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("potholes.pothole_id"))
    report_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("reports.report_id"))
    actor: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    from_status: Mapped[str | None] = mapped_column(String)
    to_status: Mapped[str | None] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(String)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _created()


class Confirmation(Base):
    __tablename__ = "confirmations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pothole_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("potholes.pothole_id"))
    device_id: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = _created()


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pothole_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("potholes.pothole_id"))
    type: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = _created()
    last_error: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = _created()
    updated_at: Mapped[datetime] = _created()


class FeedbackLabel(Base):
    __tablename__ = "feedback_labels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("reports.report_id"))
    pothole_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("potholes.pothole_id"))
    label: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)
    photo_path: Mapped[str | None] = mapped_column(String)
    model_score: Mapped[int | None] = mapped_column(SmallInteger)
    model_confidence: Mapped[float | None] = mapped_column(Float)
    boxes: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    note: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = _created()


class GeoCache(Base):
    __tablename__ = "geo_cache"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = _created()


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[uuid.UUID] = _uuid_pk()
    device_id: Mapped[str] = mapped_column(String)
    sender: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = _created()
