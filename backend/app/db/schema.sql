-- WP3 Core API schema (Sprint1_Action_Plan.md, Section 4.1)
-- Applied automatically by the `db` service via docker-entrypoint-initdb.d.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- gen_random_uuid()

CREATE TYPE report_status AS ENUM ('new', 'confirmed', 'sheet_sent', 'fixed');
CREATE TYPE report_source AS ENUM ('manual', 'driving_mode');

CREATE TABLE reports (
    report_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_report_id  text NOT NULL UNIQUE,
    photo_url         text,
    lat               double precision NOT NULL,
    lon               double precision NOT NULL,
    gps_accuracy_m    double precision,
    speed_kmh         double precision,
    direction_deg     double precision CHECK (direction_deg IS NULL OR (direction_deg >= 0 AND direction_deg <= 360)),
    captured_at       timestamptz NOT NULL,
    source            report_source NOT NULL,
    score             smallint CHECK (score IS NULL OR (score BETWEEN 1 AND 5)),
    confidence        double precision CHECK (confidence IS NULL OR (confidence BETWEEN 0 AND 1)),
    status            report_status NOT NULL DEFAULT 'new',
    cluster_id        uuid,
    -- Additive beyond Section 4.1's frozen Report object -- populated by the RAG
    -- service's generate() call once a report is confirmed with score >= 3.
    sheet_text        text,
    target_office     text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

-- Supports the <5m duplicate-merge check (ST_DWithin) without denormalizing lat/lon.
CREATE INDEX idx_reports_geog ON reports USING GIST (geography(ST_SetSRID(ST_MakePoint(lon, lat), 4326)));

CREATE INDEX idx_reports_status ON reports (status);
CREATE INDEX idx_reports_cluster_id ON reports (cluster_id);
