import os
import asyncpg
from settings import DATABASE_URL
pool = None

async def connect_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1,
        max_size=int(os.getenv("DB_POOL_SIZE", "10")), command_timeout=30, timeout=10)

async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None

async def get_db_connection():
    async with pool.acquire() as connection:
        yield connection
