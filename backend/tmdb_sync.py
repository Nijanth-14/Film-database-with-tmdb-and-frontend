"""Explicitly queue optional metadata enrichment for existing catalog entries."""
import asyncio
import os
import asyncpg
from settings import DATABASE_URL

async def main():
    if not os.getenv("TMDB_API_KEY"):
        raise SystemExit("Set TMDB_API_KEY in backend/.env first.")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        result = await conn.execute("""UPDATE media SET metadata_status='pending',
            metadata_attempts=0,metadata_retry_at=NOW() WHERE tmdb_id IS NULL""")
        print(result + "; metadata will be fetched by the running API worker.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
