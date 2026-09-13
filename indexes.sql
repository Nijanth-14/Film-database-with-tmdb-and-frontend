-- B-Tree Indexes for self-hosted multimedia platform

-- 1. Index on media title for fast searches and sorting by title
CREATE INDEX idx_media_title ON media USING btree (title);

-- 2. Index on playback_state user_id for fast retrieval of a user's resume positions
CREATE INDEX idx_playback_user ON playback_state USING btree (user_id);

-- 3. Composite index on watch_history user_id and watched_at for timeline query optimization
CREATE INDEX idx_watch_history_user_time ON watch_history USING btree (user_id, watched_at);

-- 4. Index on media_actors actor_id to optimize actor profile lookups
CREATE INDEX idx_media_actors_actor ON media_actors USING btree (actor_id);

-- 5. Index on ratings media_id for optimizing average rating queries and aggregation
CREATE INDEX idx_ratings_media ON ratings USING btree (media_id);
