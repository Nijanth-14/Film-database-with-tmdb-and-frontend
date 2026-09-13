-- Verification and Demonstration Script for Academic DBMS Project

-- ==========================================
-- 1. Concurrency UPSERT Demo
-- ==========================================
-- Demonstrates upserting a playback state record. If the user-media combination exists,
-- it performs an update of last_position and updated_at; otherwise, it inserts a new record.

-- Let's view current playback state for User 1, Media 2 (should not exist in seed_data: User 1 only has Media 1 and 5 in playback_state)
SELECT * FROM playback_state WHERE user_id = 1 AND media_id = 2;

-- Perform UPSERT (Insert action)
INSERT INTO playback_state (user_id, media_id, last_position)
VALUES (1, 2, INTERVAL '00:10:00')
ON CONFLICT (user_id, media_id) 
DO UPDATE SET 
    last_position = EXCLUDED.last_position,
    updated_at = NOW();

-- Verify insert succeeded
SELECT * FROM playback_state WHERE user_id = 1 AND media_id = 2;

-- Perform UPSERT (Update action with new timestamp and position)
INSERT INTO playback_state (user_id, media_id, last_position)
VALUES (1, 2, INTERVAL '00:25:30')
ON CONFLICT (user_id, media_id) 
DO UPDATE SET 
    last_position = EXCLUDED.last_position,
    updated_at = NOW();

-- Verify update succeeded
SELECT * FROM playback_state WHERE user_id = 1 AND media_id = 2;


-- ==========================================
-- 2. Trigger Verification (set_playback_updated_at)
-- ==========================================
-- Verify that when we update `playback_state` (excluding `updated_at`), the BEFORE UPDATE 
-- trigger automatically updates `updated_at` to the current transaction timestamp.

-- Let's check the current last_position and updated_at for User 2, Media 2
SELECT user_id, media_id, last_position, updated_at 
FROM playback_state 
WHERE user_id = 2 AND media_id = 2;

-- Update only the last_position
UPDATE playback_state 
SET last_position = INTERVAL '00:20:45'
WHERE user_id = 2 AND media_id = 2;

-- Verify that updated_at changed automatically to a newer time
SELECT user_id, media_id, last_position, updated_at 
FROM playback_state 
WHERE user_id = 2 AND media_id = 2;


-- ==========================================
-- 3. Stored Procedure Test (complete_playback)
-- ==========================================
-- Demonstrates completion of a playback session. It must atomically delete from `playback_state` 
-- and insert a corresponding entry into `watch_history`.

-- Check initial state for User 4, Media 7
SELECT 'playback_state_before' AS source, user_id, media_id, last_position, updated_at FROM playback_state WHERE user_id = 4 AND media_id = 7
UNION ALL
SELECT 'watch_history_before' AS source, user_id, media_id, NULL, watched_at FROM watch_history WHERE user_id = 4 AND media_id = 7;

-- Call the stored procedure
CALL complete_playback(4, 7);

-- Verify final state: playback_state row should be deleted, and a new watch_history entry should be created
SELECT 'playback_state_after' AS source, user_id, media_id, last_position, updated_at FROM playback_state WHERE user_id = 4 AND media_id = 7
UNION ALL
SELECT 'watch_history_after' AS source, user_id, media_id, NULL, watched_at FROM watch_history WHERE user_id = 4 AND media_id = 7;


-- ==========================================
-- 4. Analytical View Queries
-- ==========================================

-- Select top 10 most watched media items
SELECT * FROM top_watched_media;

-- Select user resume dashboard info
SELECT * FROM user_dashboard;


-- ==========================================
-- 5. EXPLAIN ANALYZE Queries (Index Utilization)
-- ==========================================

-- Verify B-Tree index utilization for media title search
EXPLAIN ANALYZE 
SELECT * FROM media 
WHERE title = 'Interstellar Journey';

-- Verify B-Tree index utilization for user history scan (by user and time)
EXPLAIN ANALYZE 
SELECT * FROM watch_history 
WHERE user_id = 1 AND watched_at >= NOW() - INTERVAL '7 days';
