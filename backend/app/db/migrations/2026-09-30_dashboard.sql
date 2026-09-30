-- Brings a database created from the Sprint 1 schema.sql up to date for the
-- authorities dashboard. Fresh databases get all of this from schema.sql.
-- (No Alembic yet: SCRUM-25.)
ALTER TYPE report_status ADD VALUE IF NOT EXISTS 'rejected';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS device_id text;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS address text;
CREATE INDEX IF NOT EXISTS idx_reports_device_id ON reports (device_id);
CREATE TABLE IF NOT EXISTS messages (
    message_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id   text NOT NULL,
    sender      text NOT NULL CHECK (sender IN ('citizen', 'authority')),
    body        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_messages_device_id ON messages (device_id, created_at);
