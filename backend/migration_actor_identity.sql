-- People may share names. Their provider IDs, not names, define identity.
-- Removes only the legacy uniqueness rule; existing actor rows and links stay intact.
ALTER TABLE actors DROP CONSTRAINT IF EXISTS actors_name_key;
