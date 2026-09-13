-- Seed Data for self-hosted multimedia platform

-- 1. Insert 5 sample users (with dummy hashed passwords)
INSERT INTO users (username, email, password_hash, created_at) VALUES
('alice_db', 'alice@example.com', '$2b$12$K3yD5h7S79x9jM2E7n6m8uN1uQ4C3e5V7r6Y8P9O0iWqT2y9X8aZ.', NOW() - INTERVAL '30 days'),
('bob_stream', 'bob@example.com', '$2b$12$R4yE6h8T80y0kN3F8o7n9vO2vR5D4f6W8s7Z9Q0P1jXrU3z0Y9bA.', NOW() - INTERVAL '25 days'),
('charlie_cine', 'charlie@example.com', '$2b$12$S5zF7i9U81z1lN4G9p8o0wP3wS6E5g7X9t8A0R1kYsYV4a1Z0cB.', NOW() - INTERVAL '20 days'),
('diana_watcher', 'diana@example.com', '$2b$12$T6aG8j0V92a2mO5H0q9p1xQ4xT7F6h8Y0u9B1S2lZtZW5b2a1dC.', NOW() - INTERVAL '15 days'),
('ethan_media', 'ethan@example.com', '$2b$12$U7bH9k1W03b3nP6I1r0q2yR5yU8G7i9Z1v0C2T3ma_aX6c3b2eD.', NOW() - INTERVAL '10 days');

-- 2. Insert 5 genres
INSERT INTO genres (name) VALUES
('Sci-Fi'),
('Action'),
('Drama'),
('Documentary'),
('Animation');

-- 3. Insert 4 languages
INSERT INTO languages (name, code) VALUES
('English', 'en'),
('Spanish', 'es'),
('French', 'fr'),
('Japanese', 'ja');

-- 4. Insert 4 production studios
INSERT INTO studios (name) VALUES
('Nexus Pictures'),
('Apex Cinema'),
('Chronos Studios'),
('Aether Animations');

-- 5. Insert 10 media items with realistic durations and paths
INSERT INTO media (title, duration, path, genre_id, language_id, studio_id, created_at) VALUES
('Interstellar Journey', INTERVAL '02:15:00', '/media/movies/interstellar_journey.mp4', 1, 1, 1, NOW() - INTERVAL '9 days'),
('Cyber Horizon 2099', INTERVAL '01:50:00', '/media/movies/cyber_horizon.mp4', 1, 1, 3, NOW() - INTERVAL '8 days'),
('The Last Stand', INTERVAL '01:38:00', '/media/movies/the_last_stand.mp4', 2, 1, 2, NOW() - INTERVAL '7 days'),
('Shadow Ninja', INTERVAL '01:25:00', '/media/movies/shadow_ninja.mp4', 2, 4, 4, NOW() - INTERVAL '6 days'),
('Echoes of Silence', INTERVAL '01:58:00', '/media/movies/echoes_silence.mp4', 3, 3, 2, NOW() - INTERVAL '5 days'),
('Bitter Harvest', INTERVAL '02:05:00', '/media/movies/bitter_harvest.mp4', 3, 2, 3, NOW() - INTERVAL '4 days'),
('Planet Earth: Deep Oceans', INTERVAL '00:52:00', '/media/docs/deep_oceans.mp4', 4, 1, 1, NOW() - INTERVAL '3 days'),
('Rethinking AI', INTERVAL '01:10:00', '/media/docs/rethinking_ai.mp4', 4, 1, 3, NOW() - INTERVAL '2 days'),
('The Forest Spirit', INTERVAL '01:32:00', '/media/movies/forest_spirit.mp4', 5, 4, 4, NOW() - INTERVAL '1 day'),
('Skyward Academy', INTERVAL '00:24:00', '/media/episodes/skyward_s01e01.mp4', 5, 1, 4, NOW() - INTERVAL '12 hours');

-- 6. Insert 10 actors
INSERT INTO actors (name) VALUES
('Liam Neeson'),
('Scarlett Johansson'),
('Ken Watanabe'),
('Marion Cotillard'),
('Cillian Murphy'),
('Timothée Chalamet'),
('Zendaya Coleman'),
('Tom Hanks'),
('Meryl Streep'),
('Christian Bale');

-- Link actors to media items via media_actors
INSERT INTO media_actors (media_id, actor_id) VALUES
(1, 6), -- Interstellar Journey - Timothée Chalamet
(1, 7), -- Interstellar Journey - Zendaya Coleman
(2, 2), -- Cyber Horizon 2099 - Scarlett Johansson
(3, 1), -- The Last Stand - Liam Neeson
(3, 10), -- The Last Stand - Christian Bale
(4, 3), -- Shadow Ninja - Ken Watanabe
(5, 4), -- Echoes of Silence - Marion Cotillard
(5, 5), -- Echoes of Silence - Cillian Murphy
(6, 9), -- Bitter Harvest - Meryl Streep
(9, 3); -- The Forest Spirit - Ken Watanabe

-- 7. Insert sample records for subtitles
INSERT INTO subtitles (media_id, language_id, file_path) VALUES
(1, 1, '/media/subtitles/interstellar_en.vtt'),
(1, 2, '/media/subtitles/interstellar_es.vtt'),
(2, 1, '/media/subtitles/cyber_horizon_en.vtt'),
(4, 1, '/media/subtitles/shadow_ninja_en.vtt'),
(4, 4, '/media/subtitles/shadow_ninja_ja.vtt'),
(5, 1, '/media/subtitles/echoes_en.vtt'),
(5, 3, '/media/subtitles/echoes_fr.vtt'),
(9, 1, '/media/subtitles/forest_spirit_en.vtt');

-- 8. Insert sample playlists
INSERT INTO playlists (user_id, name, created_at) VALUES
(1, 'Sci-Fi Classics', NOW() - INTERVAL '5 days'),
(1, 'To Watch List', NOW() - INTERVAL '4 days'),
(2, 'My Favorites', NOW() - INTERVAL '3 days'),
(3, 'Action Nights', NOW() - INTERVAL '2 days');

-- Link media to playlists via playlist_media
INSERT INTO playlist_media (playlist_id, media_id, position) VALUES
(1, 1, 1),
(1, 2, 2),
(2, 3, 1),
(2, 5, 2),
(2, 9, 3),
(3, 1, 1),
(3, 9, 2),
(4, 3, 1),
(4, 4, 2);

-- 9. Insert active playback entries in playback_state
INSERT INTO playback_state (user_id, media_id, last_position, updated_at) VALUES
(1, 1, INTERVAL '01:10:25', NOW() - INTERVAL '1 hour'),
(1, 5, INTERVAL '00:45:00', NOW() - INTERVAL '2 hours'),
(2, 2, INTERVAL '00:15:10', NOW() - INTERVAL '3 hours'),
(3, 3, INTERVAL '01:20:00', NOW() - INTERVAL '30 minutes'),
(4, 7, INTERVAL '00:30:15', NOW() - INTERVAL '10 minutes');

-- 10. Insert historical view entries in watch_history
INSERT INTO watch_history (user_id, media_id, watched_at) VALUES
(1, 1, NOW() - INTERVAL '3 days'),
(1, 3, NOW() - INTERVAL '2 days'),
(1, 7, NOW() - INTERVAL '1 day'),
(2, 1, NOW() - INTERVAL '4 days'),
(2, 3, NOW() - INTERVAL '2 days'),
(3, 1, NOW() - INTERVAL '5 days'),
(3, 5, NOW() - INTERVAL '4 days'),
(4, 1, NOW() - INTERVAL '1 day'),
(4, 8, NOW() - INTERVAL '6 hours'),
(5, 1, NOW() - INTERVAL '10 hours'),
(5, 9, NOW() - INTERVAL '2 hours');

-- 11. Insert ratings with valid scores (1-10)
INSERT INTO ratings (user_id, media_id, rating, created_at) VALUES
(1, 1, 9, NOW() - INTERVAL '3 days'),
(1, 3, 7, NOW() - INTERVAL '2 days'),
(2, 1, 10, NOW() - INTERVAL '4 days'),
(2, 2, 8, NOW() - INTERVAL '3 days'),
(3, 1, 8, NOW() - INTERVAL '5 days'),
(3, 5, 9, NOW() - INTERVAL '4 days'),
(4, 1, 9, NOW() - INTERVAL '1 day'),
(5, 1, 10, NOW() - INTERVAL '10 hours'),
(5, 9, 8, NOW() - INTERVAL '2 hours');
