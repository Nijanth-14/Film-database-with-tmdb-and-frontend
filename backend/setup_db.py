"""Create or migrate without dropping or reseeding existing data."""
import asyncio
import asyncpg
from settings import DATABASE_URL, ROOT

async def setup():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(7192026)")
            await conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations
                (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
            if not await conn.fetchval("SELECT to_regclass('public.users')"):
                await conn.execute((ROOT / "schema.sql").read_text())
                await conn.execute((ROOT / "indexes.sql").read_text())
            for version, filename in [
                ("20260928_conference_v1", "migration.sql"),
                ("20260928_actor_identity_v2", "migration_actor_identity.sql"),
                ("20260928_full_video_v3", "migration_playback_preparation.sql"),
                ("20260929_series_v4", "migration_series.sql"),
            ]:
                if not await conn.fetchval("SELECT 1 FROM schema_migrations WHERE version=$1", version):
                    await conn.execute((ROOT / "backend" / filename).read_text())
                    await conn.execute("INSERT INTO schema_migrations(version) VALUES($1)", version)
            await conn.execute((ROOT / "views.sql").read_text())
            await conn.execute((ROOT / "routines.sql").read_text().replace(
                "CREATE TRIGGER trg_set_playback_updated_at",
                "CREATE OR REPLACE TRIGGER trg_set_playback_updated_at"))
        print("Database ready. Existing data preserved.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(setup())
