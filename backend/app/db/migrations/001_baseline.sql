-- 001 · Baseline: the Sprint 1 schema plus the 2026-09-30 dashboard additions.
-- Written to be idempotent so it also runs cleanly on a database that was
-- created from the old backend/app/db/schema.sql before migrations existed.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto; -- gen_random_uuid()

DO $$ BEGIN
    CREATE TYPE report_status AS ENUM ('new', 'confirmed', 'sheet_sent', 'fixed', 'rejected');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    CREATE TYPE report_source AS ENUM ('manual', 'driving_mode');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
ALTER TYPE report_status ADD VALUE IF NOT EXISTS 'rejected';

CREATE TABLE IF NOT EXISTS reports (
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
    sheet_text        text,
    target_office     text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE reports ADD COLUMN IF NOT EXISTS device_id text;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS address text;

CREATE INDEX IF NOT EXISTS idx_reports_geog ON reports USING GIST (geography(ST_SetSRID(ST_MakePoint(lon, lat), 4326)));
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports (status);
CREATE INDEX IF NOT EXISTS idx_reports_cluster_id ON reports (cluster_id);
CREATE INDEX IF NOT EXISTS idx_reports_device_id ON reports (device_id);

-- Citizen <-> authority support chat, one thread per device.
CREATE TABLE IF NOT EXISTS messages (
    message_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id   text NOT NULL,
    sender      text NOT NULL CHECK (sender IN ('citizen', 'authority')),
    body        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_messages_device_id ON messages (device_id, created_at);
