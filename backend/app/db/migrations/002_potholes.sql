-- 002 · Potholes become a first-class entity (issue #20, roadmap decision 1).
--
-- A report is one citizen's photo; a pothole is the physical hole that one or
-- more reports describe. Status, severity, priority, routing, the work sheet
-- and the SLA all live on the pothole.

-- Statuses and sources become plain text + CHECK: easier to extend than a
-- Postgres enum (ALTER TYPE ... ADD VALUE cannot be used in the transaction
-- that adds it), and identical on the wire.
ALTER TABLE reports ALTER COLUMN status DROP DEFAULT;
ALTER TABLE reports ALTER COLUMN status TYPE text USING status::text;
ALTER TABLE reports ALTER COLUMN status SET DEFAULT 'new';
ALTER TABLE reports ALTER COLUMN source TYPE text USING source::text;
DROP TYPE IF EXISTS report_status;
DROP TYPE IF EXISTS report_source;
ALTER TABLE reports ADD CONSTRAINT reports_status_check
    CHECK (status IN ('new', 'confirmed', 'sheet_sent', 'fixed', 'rejected', 'reopened'));
ALTER TABLE reports ADD CONSTRAINT reports_source_check
    CHECK (source IN ('manual', 'driving_mode', 'web'));

CREATE TABLE potholes (
    pothole_id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    status               text NOT NULL DEFAULT 'new'
                         CHECK (status IN ('new', 'confirmed', 'sheet_sent', 'fixed', 'rejected', 'reopened')),
    lat                  double precision NOT NULL,
    lon                  double precision NOT NULL,
    report_count         integer NOT NULL DEFAULT 0,
    device_count         integer NOT NULL DEFAULT 0,
    confirm_count        integer NOT NULL DEFAULT 0,
    fixed_ok_count       integer NOT NULL DEFAULT 0,
    not_fixed_count      integer NOT NULL DEFAULT 0,
    not_pothole_count    integer NOT NULL DEFAULT 0,
    severity             smallint CHECK (severity IS NULL OR (severity BETWEEN 1 AND 5)),
    max_confidence       double precision,
    priority_score       real NOT NULL DEFAULT 0,
    priority_components  jsonb NOT NULL DEFAULT '{}'::jsonb,
    -- Filled by the OSM enrichment job (issue #24).
    road_type            text,
    road_class           text,
    road_name            text,
    road_ref             text,
    region               text,
    municipality         text,
    address_label        text,
    enrichment_source    text,
    -- Work sheet (issue #25). sheet_status: queued | generated | approved | failed.
    sheet_status         text CHECK (sheet_status IS NULL OR sheet_status IN ('queued', 'generated', 'approved', 'failed')),
    sheet_text           text,
    sheet_text_original  text,
    sheet_citations      jsonb,
    sheet_generated_at   timestamptz,
    sheet_approved_at    timestamptz,
    sheet_approved_by    text,
    sheet_hash           text,
    -- Lifecycle timestamps; SLA (issue #26).
    confirmed_at         timestamptz,
    sla_due_at           timestamptz,
    escalated_at         timestamptz,
    fixed_at             timestamptz,
    reopened_at          timestamptz,
    fixed_proof_url      text,
    fixed_note           text,
    -- AI re-check of the proof photo: {detected, confidence, score, checked_at}.
    fix_check            jsonb,
    fix_verified         boolean NOT NULL DEFAULT false,
    needs_review         boolean NOT NULL DEFAULT false,
    -- Forecast rain over the next 48 h at this spot (weather job).
    rain_mm_48h          real,
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_potholes_geog ON potholes USING GIST (geography(ST_SetSRID(ST_MakePoint(lon, lat), 4326)));
CREATE INDEX idx_potholes_status ON potholes (status);
CREATE INDEX idx_potholes_priority ON potholes (priority_score DESC);

ALTER TABLE reports ADD COLUMN pothole_id uuid REFERENCES potholes (pothole_id) ON DELETE SET NULL;
ALTER TABLE reports ADD COLUMN detected boolean NOT NULL DEFAULT false;
ALTER TABLE reports ADD COLUMN needs_review boolean NOT NULL DEFAULT false;
ALTER TABLE reports ADD COLUMN boxes jsonb;
ALTER TABLE reports ADD COLUMN inference_ms real;
CREATE INDEX idx_reports_pothole_id ON reports (pothole_id);

-- Audit trail: one row per thing that happened to a pothole (issue #20 step 5).
-- actor: 'device:<id>' | 'office:<code>' | 'system'.
CREATE TABLE report_events (
    id           bigserial PRIMARY KEY,
    pothole_id   uuid NOT NULL REFERENCES potholes (pothole_id) ON DELETE CASCADE,
    report_id    uuid REFERENCES reports (report_id) ON DELETE SET NULL,
    actor        text NOT NULL,
    kind         text NOT NULL,
    from_status  text,
    to_status    text,
    note         text,
    data         jsonb,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_report_events_pothole ON report_events (pothole_id, created_at);

-- "I see it too" and fix verification taps (issue #22).
CREATE TABLE confirmations (
    id              bigserial PRIMARY KEY,
    pothole_id      uuid NOT NULL REFERENCES potholes (pothole_id) ON DELETE CASCADE,
    device_id       text NOT NULL,
    kind            text NOT NULL CHECK (kind IN ('seen', 'fixed_ok', 'not_fixed', 'not_pothole')),
    lat             double precision,
    lon             double precision,
    gps_accuracy_m  double precision,
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (pothole_id, device_id, kind)
);

-- Backfill: one pothole per old cluster, one per unclustered report.
INSERT INTO potholes (pothole_id, status, lat, lon, report_count, device_count, severity,
                      max_confidence, address_label, sheet_text, sheet_status, created_at, updated_at)
SELECT k, last.status, agg.lat, agg.lon, agg.n, agg.devices, agg.severity, agg.conf,
       last.address, agg.sheet_text, CASE WHEN agg.sheet_text IS NOT NULL THEN 'generated' END,
       agg.created_at, agg.updated_at
FROM (
    SELECT COALESCE(cluster_id, report_id) AS k, avg(lat) AS lat, avg(lon) AS lon, count(*) AS n,
           count(DISTINCT COALESCE(device_id, device_report_id)) AS devices,
           max(score) AS severity, max(confidence) AS conf, max(sheet_text) AS sheet_text,
           min(created_at) AS created_at, max(updated_at) AS updated_at
    FROM reports GROUP BY 1
) agg
JOIN LATERAL (
    SELECT status, address FROM reports r
    WHERE COALESCE(r.cluster_id, r.report_id) = agg.k
    ORDER BY created_at DESC LIMIT 1
) last ON true;

UPDATE reports SET pothole_id = COALESCE(cluster_id, report_id), detected = score IS NOT NULL;
