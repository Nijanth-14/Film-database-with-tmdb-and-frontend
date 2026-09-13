import asyncpg
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to use standard postgres port 5432 and database multimedia_db
# Defaults to localhost with user postgres
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/multimedia_db")

pool = None

async def connect_db():
    global pool
    try:
        # We'll allow falling back to local unix socket if password is not needed 
        # or connecting as the current user. 
        # We will first try to use DATABASE_URL. If it fails with role "postgres" does not exist,
        # we can try without the username.
        pool = await asyncpg.create_pool(DATABASE_URL)
        logger.info("Connected to PostgreSQL database.")
    except Exception as e:
        logger.warning(f"Failed to connect to database using default URL: {e}")
        try:
            # Fallback for local WSL environments where the user is the postgres role
            pool = await asyncpg.create_pool(database="multimedia_db")
            logger.info("Connected to PostgreSQL database using local unix socket.")
        except Exception as fallback_error:
             logger.error(f"Fallback connection failed: {fallback_error}")

async def close_db():
    global pool
    if pool:
        await pool.close()
        logger.info("Closed PostgreSQL database connection.")

async def get_db_connection():
    global pool
    if not pool:
        await connect_db()
    
    if pool:
        async with pool.acquire() as connection:
            yield connection
    else:
        raise Exception("Database pool is not initialized")
