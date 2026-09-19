"""SQLite storage -- explicit, documented stand-in for Supabase/PostGIS (see README).

Field names match Section 4.1's Report object exactly, plus two glue-only
additive columns (sheet_text, target_office) not in the frozen contract.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    device_report_id TEXT NOT NULL,
    photo_url TEXT,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    gps_accuracy_m REAL,
    speed_kmh REAL,
    direction_deg REAL,
    captured_at TEXT,
    source TEXT,
    score INTEGER,
    confidence REAL,
    status TEXT NOT NULL DEFAULT 'new',
    cluster_id TEXT,
    sheet_text TEXT,
    target_office TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_device_report_id ON reports(device_report_id);
CREATE INDEX IF NOT EXISTS idx_cluster_id ON reports(cluster_id);
"""


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(_SCHEMA)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.REPORTS_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
