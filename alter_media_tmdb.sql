-- Add TMDB specific columns to the media table

ALTER TABLE media
ADD COLUMN IF NOT EXISTS tmdb_id INT UNIQUE,
ADD COLUMN IF NOT EXISTS poster_path TEXT,
ADD COLUMN IF NOT EXISTS backdrop_path TEXT,
ADD COLUMN IF NOT EXISTS overview TEXT;
