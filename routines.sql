-- Trigger Functions and Stored Procedures for self-hosted multimedia platform

-- 1. Row-level BEFORE UPDATE trigger function set_playback_updated_at()
CREATE OR REPLACE FUNCTION set_playback_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger definition on playback_state table
CREATE TRIGGER trg_set_playback_updated_at
BEFORE UPDATE ON playback_state
FOR EACH ROW
EXECUTE FUNCTION set_playback_updated_at();

-- 2. Stored procedure complete_playback(p_user_id INT, p_media_id INT)
-- Executes an atomic transaction to delete the record from playback_state and insert a new record into watch_history.
CREATE OR REPLACE PROCEDURE complete_playback(
    p_user_id INT,
    p_media_id INT
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Delete from playback_state
    DELETE FROM playback_state
    WHERE user_id = p_user_id AND media_id = p_media_id;

    -- Insert into watch_history
    INSERT INTO watch_history (user_id, media_id, watched_at)
    VALUES (p_user_id, p_media_id, NOW());
END;
$$;
