import asyncio
import os
import httpx
import logging
from dotenv import load_dotenv

import database

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

async def sync_media():
    if not TMDB_API_KEY:
        logger.error("TMDB_API_KEY is not set. Please add it to your .env file.")
        return

    logger.info("Connecting to database...")
    await database.connect_db()
    pool = database.pool

    if not pool:
        logger.error("Failed to connect to the database.")
        return

    try:
        async with pool.acquire() as conn:
            # Fetch all media that do not have a TMDB ID yet
            media_items = await conn.fetch("SELECT id, title, path FROM media WHERE tmdb_id IS NULL")
            
            if not media_items:
                logger.info("All media items already have TMDB metadata synced.")
                return

            logger.info(f"Found {len(media_items)} media items to sync.")

            async with httpx.AsyncClient() as client:
                for item in media_items:
                    media_id = item["id"]
                    title = item["title"]
                    # We can use the file path or some other logic to determine if it's a TV show or movie, 
                    # but for now, we'll just search movies.
                    
                    is_tv = "episodes" in item["path"]
                    search_type = "tv" if is_tv else "movie"
                    
                    logger.info(f"Searching TMDB for {search_type}: '{title}'...")
                    
                    response = await client.get(
                        f"{TMDB_BASE_URL}/search/{search_type}",
                        params={
                            "api_key": TMDB_API_KEY,
                            "query": title,
                            "page": 1,
                            "include_adult": "false"
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", [])
                        
                        if results:
                            # Take the first result
                            top_result = results[0]
                            tmdb_id = top_result.get("id")
                            poster_path = top_result.get("poster_path")
                            backdrop_path = top_result.get("backdrop_path")
                            overview = top_result.get("overview")
                            
                            # Update the database
                            await conn.execute(
                                """
                                UPDATE media 
                                SET tmdb_id = $1, poster_path = $2, backdrop_path = $3, overview = $4 
                                WHERE id = $5
                                """,
                                tmdb_id, poster_path, backdrop_path, overview, media_id
                            )
                            logger.info(f"Successfully synced '{title}'.")
                        else:
                            logger.warning(f"No results found on TMDB for '{title}'.")
                    else:
                        logger.error(f"Failed to fetch data from TMDB for '{title}'. Status code: {response.status_code}")
                        
    except Exception as e:
        logger.error(f"An error occurred during sync: {e}")
    finally:
        await database.close_db()

if __name__ == "__main__":
    asyncio.run(sync_media())
