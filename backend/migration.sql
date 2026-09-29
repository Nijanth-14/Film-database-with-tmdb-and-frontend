-- Additive migration; preserve existing catalog, profiles and history.
ALTER TABLE media ADD COLUMN IF NOT EXISTS tmdb_rating NUMERIC(3,1);
ALTER TABLE media ADD COLUMN IF NOT EXISTS media_type TEXT NOT NULL DEFAULT 'movie';
ALTER TABLE media ADD COLUMN IF NOT EXISTS metadata_status TEXT NOT NULL DEFAULT 'skipped';
ALTER TABLE media ADD COLUMN IF NOT EXISTS metadata_attempts INT NOT NULL DEFAULT 0;
ALTER TABLE media ADD COLUMN IF NOT EXISTS metadata_retry_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE media DROP CONSTRAINT IF EXISTS media_tmdb_id_key;
CREATE INDEX IF NOT EXISTS idx_media_tmdb ON media (media_type, tmdb_id);
ALTER TABLE actors ADD COLUMN IF NOT EXISTS tmdb_id INT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_actor_tmdb ON actors (tmdb_id);
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE;
CREATE TABLE IF NOT EXISTS auth_sessions (
 token_hash TEXT PRIMARY KEY,
 user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_expiry ON auth_sessions (expires_at);
CREATE TABLE IF NOT EXISTS playback_sessions (
 id UUID PRIMARY KEY,
 user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 media_id INT NOT NULL REFERENCES media(id) ON DELETE CASCADE,
 completed BOOLEAN NOT NULL DEFAULT FALSE,
 last_sequence BIGINT NOT NULL DEFAULT -1,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE watch_history ADD COLUMN IF NOT EXISTS playback_session_id UUID;
CREATE UNIQUE INDEX IF NOT EXISTS idx_history_session ON watch_history (playback_session_id);
CREATE INDEX IF NOT EXISTS idx_history_media ON watch_history (media_id);
CREATE INDEX IF NOT EXISTS idx_playback_recent ON playback_state (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_media_genre_page ON media (genre_id, id);
CREATE INDEX IF NOT EXISTS idx_media_title_search ON media USING gin (to_tsvector('simple', title));
