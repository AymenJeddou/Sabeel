-- 003 · Offices and officer tokens (issue #21).
--
-- kind: 'Municipality' | 'DGPC' | 'Ministry of Equipment'. Escalation walks
-- parent_office_id (municipality -> regional directorate -> ministry).
-- token_hash is SHA-256 of the bearer token; the token itself is never stored.

CREATE TABLE offices (
    office_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code              text NOT NULL UNIQUE,
    name              text NOT NULL,
    kind              text NOT NULL CHECK (kind IN ('Municipality', 'DGPC', 'Ministry of Equipment')),
    region            text,
    municipality      text,
    lat               double precision,
    lon               double precision,
    parent_office_id  uuid REFERENCES offices (office_id),
    token_hash        text UNIQUE,
    created_at        timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE potholes ADD COLUMN target_office_id uuid REFERENCES offices (office_id);
CREATE INDEX idx_potholes_office ON potholes (target_office_id);
