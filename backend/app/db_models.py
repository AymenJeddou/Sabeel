"""SQLAlchemy models mirroring backend/app/db/schema.sql."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, Float, String, func
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
    # timezone=True matches schema.sql's `timestamptz` columns -- without it,
    # SQLAlchemy generates a `::TIMESTAMP WITHOUT TIME ZONE` cast that asyncpg
    # rejects for the timezone-aware datetimes this app actually passes
    # ("can't subtract offset-naive and offset-aware datetimes").
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # values_callable=... is required: SQLAlchemy's Enum type defaults to
    # sending the Python member NAME ("MANUAL") rather than its .value
    # ("manual"), which doesn't match the lowercase labels the Postgres enum
    # type was actually created with in schema.sql (invalid input value for
    # enum report_source: "MANUAL").
    source: Mapped[ReportSource] = mapped_column(
        SAEnum(ReportSource, name="report_source", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    score: Mapped[int | None] = mapped_column(nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        SAEnum(ReportStatus, name="report_status", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=ReportStatus.NEW,
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    sheet_text: Mapped[str | None] = mapped_column(String, nullable=True)
    target_office: Mapped[str | None] = mapped_column(String, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String, nullable=True)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    # server_default (not just the DB's own DEFAULT now()) tells SQLAlchemy to
    # omit these columns from the INSERT entirely when unset, instead of
    # explicitly sending NULL and hitting the NOT NULL constraint.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("score IS NULL OR (score BETWEEN 1 AND 5)", name="score_range"),
        CheckConstraint("confidence IS NULL OR (confidence BETWEEN 0 AND 1)", name="confidence_range"),
    )


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String, nullable=False)
    sender: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
