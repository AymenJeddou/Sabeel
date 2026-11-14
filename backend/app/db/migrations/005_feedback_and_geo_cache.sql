-- 005 · Model feedback labels (issue #28) and the OSM lookup cache (issue #24).

-- Every "not a pothole" / "confirmed pothole" decision becomes a training label.
CREATE TABLE feedback_labels (
    id                bigserial PRIMARY KEY,
    report_id         uuid REFERENCES reports (report_id) ON DELETE SET NULL,
    pothole_id        uuid REFERENCES potholes (pothole_id) ON DELETE CASCADE,
    label             text NOT NULL CHECK (label IN ('not_pothole', 'confirmed_pothole')),
    source            text NOT NULL CHECK (source IN ('officer', 'citizen')),
    photo_path        text,
    model_score       smallint,
    model_confidence  double precision,
    boxes             jsonb,
    note              text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (report_id, label)
);

-- Keyed by coordinates rounded to ~30 m so the same place never triggers a
-- second call to the public Overpass / Nominatim servers.
CREATE TABLE geo_cache (
    key         text PRIMARY KEY,
    data        jsonb NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);
