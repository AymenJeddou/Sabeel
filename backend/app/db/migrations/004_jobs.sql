-- 004 · Background jobs (issues #24, #25): one table for every job type.
-- type: 'enrich' (OSM lookup) | 'sheet' (RAG work sheet).
-- Workers claim rows with SELECT ... FOR UPDATE SKIP LOCKED, so several API
-- instances can run the worker at the same time without double work.

CREATE TABLE jobs (
    id               bigserial PRIMARY KEY,
    pothole_id       uuid NOT NULL REFERENCES potholes (pothole_id) ON DELETE CASCADE,
    type             text NOT NULL CHECK (type IN ('enrich', 'sheet')),
    status           text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'done', 'failed')),
    attempts         integer NOT NULL DEFAULT 0,
    next_attempt_at  timestamptz NOT NULL DEFAULT now(),
    last_error       text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);
-- At most one live job of each type per pothole.
CREATE UNIQUE INDEX uq_jobs_live ON jobs (pothole_id, type) WHERE status IN ('queued', 'running');
CREATE INDEX idx_jobs_due ON jobs (next_attempt_at) WHERE status = 'queued';

-- Existing potholes have never been enriched or routed.
INSERT INTO jobs (pothole_id, type) SELECT pothole_id, 'enrich' FROM potholes;
