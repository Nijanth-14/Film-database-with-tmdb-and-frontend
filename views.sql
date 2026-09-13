-- Views for self-hosted multimedia platform

-- 1. top_watched_media: Aggregate view count from watch_history grouped by media, ordered descending, limit 10.
CREATE OR REPLACE VIEW top_watched_media AS
SELECT 
    m.id AS media_id,
    m.title,
    m.poster_path,
    COUNT(wh.id) AS view_count
FROM media m
JOIN watch_history wh ON m.id = wh.media_id
GROUP BY m.id, m.title, m.poster_path
ORDER BY view_count DESC, m.id ASC
LIMIT 10;

-- 2. user_dashboard: Join users, playback_state, and media to show user resume positions with media metadata.
CREATE OR REPLACE VIEW user_dashboard AS
SELECT 
    u.id AS user_id,
    u.username,
    u.email,
    ps.media_id,
    m.title AS media_title,
    m.duration AS total_duration,
    ps.last_position,
    ps.updated_at AS last_watched_at,
    m.poster_path,
    m.backdrop_path
FROM users u
JOIN playback_state ps ON u.id = ps.user_id
JOIN media m ON ps.media_id = m.id;
