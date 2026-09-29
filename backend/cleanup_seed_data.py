"""Remove only the original seed accounts/media and unreferenced metadata."""
import asyncio
import asyncpg
from settings import DATABASE_URL

SEED_USERS = ['alice_db', 'bob_stream', 'charlie_cine', 'diana_watcher', 'ethan_media']
SEED_MEDIA = [('Interstellar Journey', '/media/movies/interstellar_journey.mp4'), ('Cyber Horizon 2099', '/media/movies/cyber_horizon.mp4'), ('The Last Stand', '/media/movies/the_last_stand.mp4'), ('Shadow Ninja', '/media/movies/shadow_ninja.mp4'), ('Echoes of Silence', '/media/movies/echoes_silence.mp4'), ('Bitter Harvest', '/media/movies/bitter_harvest.mp4'), ('Planet Earth: Deep Oceans', '/media/docs/deep_oceans.mp4'), ('Rethinking AI', '/media/docs/rethinking_ai.mp4'), ('The Forest Spirit', '/media/movies/forest_spirit.mp4'), ('Skyward Academy', '/media/episodes/skyward_s01e01.mp4')]

async def cleanup():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        async with conn.transaction():
            print(await conn.execute("DELETE FROM users WHERE username=ANY($1::text[])", SEED_USERS))
            for title, path in SEED_MEDIA:
                await conn.execute("DELETE FROM media WHERE title=$1 AND path=$2", title, path)
            for table, condition in [
                ('actors', 'NOT EXISTS (SELECT 1 FROM media_actors WHERE actor_id=actors.id)'),
                ('studios', 'NOT EXISTS (SELECT 1 FROM media WHERE studio_id=studios.id)'),
                ('genres', 'NOT EXISTS (SELECT 1 FROM media WHERE genre_id=genres.id)'),
                ('languages', 'NOT EXISTS (SELECT 1 FROM media WHERE language_id=languages.id) AND NOT EXISTS (SELECT 1 FROM subtitles WHERE language_id=languages.id)'),
            ]:
                print(table, await conn.execute('DELETE FROM ' + table + ' WHERE ' + condition))
            print('Remaining profiles:', ', '.join([row['username'] for row in await conn.fetch("SELECT username FROM users ORDER BY username")]))
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(cleanup())
