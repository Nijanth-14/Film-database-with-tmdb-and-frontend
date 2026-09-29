"""TMDB metadata, explicit match correction, and a durable background queue."""
import asyncio
import logging
import os
import re
import httpx
import database
log = logging.getLogger(__name__)
# The tmdb.org API hostname is reachable on networks that time out on themoviedb.org.
BASE_URL = "https://api.tmdb.org/3"
TIMEOUT = httpx.Timeout(15, connect=5)

def api_key():
    key = os.getenv("TMDB_API_KEY", "")
    if not key or key == "your_api_key_here":
        raise ValueError("Configure TMDB_API_KEY in backend/.env to load movie details.")
    return key

def failure_message(exc):
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code in (401,403):
            return "TMDB rejected the API key. Check TMDB_API_KEY in backend/.env."
        if exc.response.status_code == 429:
            return "TMDB is busy. Please retry shortly."
        return "TMDB could not return these details. Please retry."
    if isinstance(exc, httpx.RequestError):
        return "Cannot reach TMDB. Check the internet connection and retry."
    if isinstance(exc, ValueError):
        return str(exc)
    return "Movie details could not be saved. Please retry."

async def search(client, query, kind, key, year=None):
    query = query.strip()
    if year:
        query = re.sub(r"\s*\(?"+str(year)+r"\)?\s*$", "", query).strip() or query
    params = {"api_key": key, "query": query, "include_adult": "false"}
    if year:
        params["year" if kind == "movie" else "first_air_date_year"] = year
    response = await client.get(f"/search/{kind}", params=params)
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results and year:
        params.pop("year" if kind == "movie" else "first_air_date_year",None)
        response = await client.get(f"/search/{kind}",params=params)
        response.raise_for_status()
        results = response.json().get("results", [])
    return results

async def save_details(media_id, kind, tmdb_id, client, key):
    response = await client.get(f"/{kind}/{tmdb_id}",
        params={"api_key":key, "append_to_response":"credits"})
    response.raise_for_status()
    details = response.json()
    async with database.pool.acquire() as conn:
        async with conn.transaction():
            target = await conn.fetchrow("SELECT id,series_key FROM media WHERE id=$1 FOR UPDATE",media_id)
            if not target:
                return
            genre_id = studio_id = language_id = None
            if details.get("genres"):
                genre_id = await conn.fetchval("""INSERT INTO genres(name) VALUES($1)
                    ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name RETURNING id""",
                    details["genres"][0]["name"])
            if details.get("production_companies"):
                studio_id = await conn.fetchval("""INSERT INTO studios(name) VALUES($1)
                    ON CONFLICT(name) DO UPDATE SET name=EXCLUDED.name RETURNING id""",
                    details["production_companies"][0]["name"])
            code = details.get("original_language")
            if code:
                language = next((x.get("english_name") or x.get("name") for x in
                    details.get("spoken_languages",[]) if x.get("iso_639_1")==code), code)
                language_id = await conn.fetchval("SELECT id FROM languages WHERE code=$1 OR name=$2 LIMIT 1",code,language)
                if not language_id:
                    language_id = await conn.fetchval("""INSERT INTO languages(name,code) VALUES($1,$2)
                        ON CONFLICT(code) DO UPDATE SET name=EXCLUDED.name RETURNING id""",language,code)
            await conn.execute("""UPDATE media SET tmdb_id=$2,poster_path=$3,backdrop_path=$4,
                overview=$5,tmdb_rating=$6,genre_id=$7,studio_id=$8,language_id=$9,
                metadata_status='ready',title=$10,media_type=$11 WHERE id=$1""",
                media_id,details["id"],details.get("poster_path"),details.get("backdrop_path"),
                details.get("overview"),details.get("vote_average"),genre_id,studio_id,language_id,
                details.get("title") or details.get("name") or "Untitled",kind)
            # Match corrections replace previous cast instead of accumulating unrelated actors.
            await conn.execute("DELETE FROM media_actors WHERE media_id=$1",media_id)
            for actor in details.get("credits",{}).get("cast",[])[:12]:
                actor_id = await conn.fetchval("""INSERT INTO actors(name,tmdb_id) VALUES($1,$2)
                    ON CONFLICT(tmdb_id) DO UPDATE SET name=EXCLUDED.name RETURNING id""",actor["name"],actor["id"])
                await conn.execute("INSERT INTO media_actors VALUES($1,$2) ON CONFLICT DO NOTHING",media_id,actor_id)
            if kind == "tv":
                siblings=await conn.fetch("""UPDATE media m SET title=s.title,tmdb_id=s.tmdb_id,
                    poster_path=s.poster_path,backdrop_path=s.backdrop_path,overview=s.overview,
                    tmdb_rating=s.tmdb_rating,genre_id=s.genre_id,studio_id=s.studio_id,
                    language_id=s.language_id,metadata_status='ready'
                    FROM media s WHERE s.id=$1 AND m.id<>s.id AND m.media_type='tv'
                    AND ((m.series_key=$2 AND $2 IS NOT NULL) OR m.tmdb_id=$3) RETURNING m.id""",
                    media_id,target["series_key"],details["id"])
                ids=[r["id"] for r in siblings]
                if ids:
                    await conn.execute("DELETE FROM media_actors WHERE media_id=ANY($1::int[])",ids)
                    await conn.execute("""INSERT INTO media_actors(media_id,actor_id)
                        SELECT unnest($1::int[]),actor_id FROM media_actors WHERE media_id=$2
                        ON CONFLICT DO NOTHING""",ids,media_id)


async def enrich(item, client, key):
    if item.get("tmdb_id"):
        return await save_details(item["id"],item["media_type"],item["tmdb_id"],client,key)
    results = await search(client,item["title"],item["media_type"],key,item.get("release_year"))
    if not results:
        async with database.pool.acquire() as conn:
            await conn.execute("UPDATE media SET metadata_status='not_found' WHERE id=$1",item["id"])
        return
    await save_details(item["id"],item["media_type"],results[0]["id"],client,key)

async def worker():
    try:
        key = api_key()
    except ValueError:
        return
    async with httpx.AsyncClient(base_url=BASE_URL,timeout=TIMEOUT) as client:
        while True:
            try:
                async with database.pool.acquire() as conn:
                    item = await conn.fetchrow("""UPDATE media SET metadata_status='processing',
                        metadata_attempts=metadata_attempts+1,metadata_retry_at=NOW()+INTERVAL '2 minutes'
                        WHERE id=(SELECT id FROM media WHERE metadata_status IN ('pending','processing')
                        AND metadata_retry_at<=NOW() AND metadata_attempts<3
                        ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *""")
                    await conn.execute("""UPDATE media SET metadata_status='failed'
                        WHERE metadata_status='processing' AND metadata_attempts>=3 AND metadata_retry_at<NOW()""")
                if item:
                    try:
                        await enrich(item,client,key)
                    except Exception as exc:
                        log.warning("Metadata lookup failed for media %s: %s",item["id"],failure_message(exc))
                        async with database.pool.acquire() as conn:
                            await conn.execute("""UPDATE media SET metadata_status=$2,
                                metadata_retry_at=NOW()+INTERVAL '30 seconds' WHERE id=$1""",
                                item["id"],"failed" if item["metadata_attempts"]>=3 else "pending")
                else:
                    await asyncio.sleep(3)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.warning("Metadata worker unavailable; retrying.")
                await asyncio.sleep(5)
