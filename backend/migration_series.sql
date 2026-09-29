ALTER TABLE media ADD COLUMN IF NOT EXISTS series_key TEXT;
UPDATE media SET series_key='name:' || regexp_replace(lower(title),'[^[:alnum:]]','','g')
    || ':' || COALESCE(release_year::text,'') WHERE media_type='tv' AND series_key IS NULL;
CREATE INDEX IF NOT EXISTS idx_media_series_key ON media(series_key);
CREATE OR REPLACE VIEW media_library_groups AS
SELECT id, CASE WHEN media_type='tv' THEN COALESCE('tv:'||tmdb_id::text,series_key,'episode:'||id::text)
    ELSE 'movie:'||id::text END AS group_key FROM media;
CREATE OR REPLACE VIEW library_entries AS
SELECT mg.group_key,MIN(m.id) AS representative_id,COUNT(*)::int AS episode_count,
    COUNT(DISTINCT COALESCE(m.season_number,1))::int AS season_count
FROM media_library_groups mg JOIN media m ON m.id=mg.id GROUP BY mg.group_key;
