"""STREAM: authenticated local media library and resumable playback."""
import asyncio
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager, suppress
from typing import Literal
from urllib.parse import urlsplit
from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
import asyncpg
import guessit
import httpx
from settings import ROOT, MEDIA_ROOT
import database
import auth
import metadata
import series
import video_processing
from media_files import resolve_media_file, playback_file, list_import_files, resolve_import_folder

log = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app):
    await database.connect_db()
    async with database.pool.acquire() as conn:
        if not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name='media' AND column_name='series_key')"):
            await database.close_db()
            raise RuntimeError("Run python backend/setup_db.py before starting the server.")
    tasks = [asyncio.create_task(metadata.worker()), asyncio.create_task(video_processing.worker())]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task
        await database.close_db()

app = FastAPI(title="STREAM Media Library", lifespan=lifespan)
app.include_router(auth.router)

@app.middleware("http")
async def protect_browser_writes(request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Cross-site writes are not allowed."}, status_code=403)
        if origin and urlsplit(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Use the same origin for the website and API."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response

@app.exception_handler(asyncpg.PostgresError)
async def database_error(request, exc):
    log.error("Database operation failed: %s", type(exc).__name__)
    return JSONResponse({"detail": "Database operation failed. Please retry."}, status_code=500)

@app.get("/api/health")
async def health():
    async with database.pool.acquire() as conn:
        await conn.fetchval("SELECT 1")
    return {"status": "ok", "database": "connected"}

# All catalog surfaces return a consistent card shape, independent of pagination.
CARD = """SELECT m.id,m.title,m.duration,m.poster_path,m.backdrop_path,m.overview,
    m.tmdb_rating,m.metadata_status,m.playback_status,m.prepare_progress,m.prepare_error,
    m.media_type,m.season_number,m.episode_number,g.name AS genre,l.name AS language,s.name AS studio
    FROM media m LEFT JOIN genres g ON g.id=m.genre_id
    LEFT JOIN languages l ON l.id=m.language_id LEFT JOIN studios s ON s.id=m.studio_id"""

LIBRARY_CARD = CARD.replace("SELECT m.id", """SELECT e.group_key,e.episode_count,e.season_count,
    CASE WHEN m.media_type='tv' THEN 'series' ELSE 'movie' END AS item_kind,m.id""") + """
    JOIN library_entries e ON e.representative_id=m.id """

def card(row):
    result = dict(row)
    result["duration"] = row["duration"].total_seconds()
    if "tmdb_rating" in result:
        result["tmdb_rating"] = float(row["tmdb_rating"]) if row["tmdb_rating"] is not None else None
    for key in ("last_position",):
        if key in result and result[key] is not None:
            result[key] = result[key].total_seconds()
    for key in ("last_watched_at",):
        if key in result and result[key] is not None:
            result[key] = result[key].isoformat()
    return result

@app.get("/api/genres")
async def genres(user=Depends(auth.current_user)):
    async with database.pool.acquire() as conn:
        return [r["name"] for r in await conn.fetch("SELECT name FROM genres ORDER BY name")]

@app.get("/api/catalog")
async def catalog(q: str = Query("", max_length=200), genre: str = Query("", max_length=100),
                  after: int = Query(0, ge=0), limit: int = Query(24, ge=1, le=100),
                  user=Depends(auth.current_user)):
    words = re.findall(r"\w+", q, flags=re.UNICODE)
    tsquery = " & ".join(word + ":*" for word in words)
    async with database.pool.acquire() as conn:
        rows = await conn.fetch(LIBRARY_CARD + """ WHERE m.id>$1
            AND ($2='' OR to_tsvector('simple',m.title) @@ to_tsquery('simple',$2))
            AND ($3='' OR g.name=$3) ORDER BY m.id LIMIT $4""",
            after, tsquery, genre, limit+1)
    return {"items": [card(r) for r in rows[:limit]],
            "next_cursor": rows[limit-1]["id"] if len(rows)>limit else None}

@app.get("/api/catalog/{media_id}")
async def media_detail(media_id: int, user=Depends(auth.current_user)):
    async with database.pool.acquire() as conn:
        row = await conn.fetchrow(CARD+" WHERE m.id=$1", media_id)
        if not row:
            raise HTTPException(404, "Media not found.")
        result = card(row)
        result["actors"] = [r["name"] for r in await conn.fetch("""SELECT a.name FROM actors a
            JOIN media_actors ma ON a.id=ma.actor_id WHERE ma.media_id=$1 ORDER BY a.id""", media_id)]
        result["rating"] = await conn.fetchval("SELECT rating FROM ratings WHERE user_id=$1 AND media_id=$2",
                                               user["id"], media_id)
        file_row = await conn.fetchrow("SELECT path,prepared_path,playback_status,prepare_error FROM media WHERE id=$1", media_id)
    try:
        playback_file(file_row)
        result["available"] = True
    except HTTPException:
        # Source file can still be live-transcoded even without preparation.
        try:
            resolve_media_file(file_row["path"])
            result["available"] = True
        except HTTPException:
            result["available"] = False
    return result

@app.get("/api/dashboard")
async def dashboard(user=Depends(auth.current_user)):
    async with database.pool.acquire() as conn:
        rows = await conn.fetch("""SELECT m.id,m.title,m.duration,m.poster_path,m.backdrop_path,
            m.tmdb_rating,m.playback_status,m.prepare_progress,m.media_type,m.season_number,m.episode_number,g.name AS genre,ps.last_position,ps.updated_at AS last_watched_at
            FROM playback_state ps JOIN media m ON m.id=ps.media_id
            LEFT JOIN genres g ON g.id=m.genre_id WHERE ps.user_id=$1
            ORDER BY ps.updated_at DESC LIMIT 24""", user["id"])
    return [card(r) for r in rows]

@app.get("/api/trending")
async def trending(user=Depends(auth.current_user)):
    async with database.pool.acquire() as conn:
        rows=await conn.fetch(LIBRARY_CARD.replace("SELECT e.group_key",
            "SELECT COALESCE(v.view_count,0) AS view_count,e.group_key") + """
            LEFT JOIN (SELECT mg.group_key,COUNT(wh.id) AS view_count
                FROM media_library_groups mg JOIN watch_history wh ON wh.media_id=mg.id
                GROUP BY mg.group_key) v ON v.group_key=e.group_key
            ORDER BY COALESCE(v.view_count,0) DESC,m.id DESC LIMIT 10""")
    return [card(r) for r in rows]

@app.get("/api/series/{media_id}")
async def series_detail(media_id:int,user=Depends(auth.current_user)):
    async with database.pool.acquire() as conn:
        return await series.get_series(conn,media_id,user["id"])

class ImportPath(BaseModel):
    path: str = Field(min_length=1, max_length=2000)

class AddMedia(ImportPath):
    title: str = Field("", max_length=300)
    media_type: Literal["auto", "movie", "tv"] = "auto"
    fetch_metadata: bool = True
    # Legacy clients may send this; the actual duration is always read from the file.
    duration_seconds: int | None = None

async def inspect_import(value):
    path = resolve_media_file(value)
    try:
        info = await video_processing.inspect_video(path)
    except asyncio.TimeoutError:
        raise HTTPException(422, "Reading this video timed out. Check that the file is fully downloaded.")
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, str(exc))
    return path, info, video_processing.detect_identity(path)

@app.post("/api/import/folder/scan")
async def scan_import_folder(data:ImportPath,user=Depends(auth.admin_user)):
    return {"items":await asyncio.to_thread(series.scan_folder,data.path)}

@app.get("/api/import/files")
async def import_files(q: str = Query("",max_length=300),user=Depends(auth.admin_user)):
    return await asyncio.to_thread(list_import_files,q)

@app.get("/api/metadata/search")
async def metadata_search(q: str = Query(min_length=2,max_length=300),
                          user=Depends(auth.admin_user)):
    try:
        key=metadata.api_key()
        async with httpx.AsyncClient(base_url=metadata.BASE_URL,timeout=metadata.TIMEOUT) as client:
            results=await asyncio.gather(metadata.search(client,q,"movie",key),
                                         metadata.search(client,q,"tv",key))
        return [{"id":r["id"],"media_type":kind,"title":r.get("title") or r.get("name"),
                 "date":r.get("release_date") or r.get("first_air_date"),"poster_path":r.get("poster_path"),
                 "overview":r.get("overview"),"rating":r.get("vote_average")}
                for kind,rows in zip(("movie","tv"),results) for r in rows[:10]]
    except (httpx.HTTPError,ValueError) as exc:
        raise HTTPException(502,metadata.failure_message(exc))

class MetadataMatch(BaseModel):
    tmdb_id: int = Field(gt=0)
    media_type: Literal["movie","tv"]

@app.post("/api/catalog/{media_id}/metadata")
async def match_metadata(media_id:int,data:MetadataMatch,user=Depends(auth.admin_user)):
    async with database.pool.acquire() as conn:
        if not await conn.fetchval("SELECT id FROM media WHERE id=$1",media_id):
            raise HTTPException(404,"Media not found.")
    try:
        async with httpx.AsyncClient(base_url=metadata.BASE_URL,timeout=metadata.TIMEOUT) as client:
            await metadata.save_details(media_id,data.media_type,data.tmdb_id,client,metadata.api_key())
    except (httpx.HTTPError,ValueError) as exc:
        raise HTTPException(502,metadata.failure_message(exc))
    return {"status":"success"}

@app.post("/api/catalog/{media_id}/metadata/retry")
async def retry_metadata(media_id:int,user=Depends(auth.admin_user)):
    try:
        metadata.api_key()
    except ValueError as exc:
        raise HTTPException(503,str(exc))
    async with database.pool.acquire() as conn:
        result=await conn.execute("""UPDATE media SET metadata_status='pending',metadata_attempts=0,
            metadata_retry_at=NOW() WHERE id=$1""",media_id)
    if result=="UPDATE 0":
        raise HTTPException(404,"Media not found.")
    return {"status":"queued"}

@app.post("/api/import/inspect")
async def inspect_import_endpoint(data: ImportPath, user=Depends(auth.admin_user)):
    folder = await asyncio.to_thread(resolve_import_folder, data.path)
    if folder is not None:
        return {"kind": "folder", "path": str(folder)}
    _, info, identity = await inspect_import(data.path)
    return {**identity, "duration_seconds": info["duration_seconds"],
            "requires_preparation": not info["direct"]}

@app.post("/api/catalog", status_code=201)
async def add_media(data: AddMedia, user=Depends(auth.admin_user)):
    path = resolve_media_file(data.path)
    stored = str(path.relative_to(MEDIA_ROOT)) if path.is_relative_to(MEDIA_ROOT) else str(path)
    async with database.pool.acquire() as conn:
        if await conn.fetchval("SELECT id FROM media WHERE path=$1 OR path=$2", stored, str(path)):
            raise HTTPException(409, "This file is already in the catalog.")
    path, info, identity = await inspect_import(data.path)
    title = data.title.strip() or identity["title"]
    kind = identity["media_type"] if data.media_type == "auto" else data.media_type
    status = "pending" if data.fetch_metadata and os.getenv("TMDB_API_KEY") else "skipped"
    playback_status = "ready" if info["direct"] else "pending"
    group_key = series.series_key(title,identity["release_year"]) if kind=="tv" else None
    async with database.pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SELECT pg_advisory_xact_lock(hashtext($1))", stored)
            if await conn.fetchval("SELECT id FROM media WHERE path=$1 OR path=$2", stored, str(path)):
                raise HTTPException(409, "This file is already in the catalog.")
            row = await conn.fetchrow("""INSERT INTO media(title,path,duration,media_type,metadata_status,
                playback_status,season_number,episode_number,release_year,series_key)
                VALUES($1,$2,make_interval(secs:=$3),$4,$5,$6,$7,$8,$9,$10) RETURNING id,title""",
                title,stored,info["duration_seconds"],kind,status,playback_status,
                identity["season_number"],identity["episode_number"],identity["release_year"],group_key)
            if group_key:
                # Reuse already-fetched series metadata for newly added episodes.
                source=await conn.fetchrow("""SELECT * FROM media WHERE series_key=$1
                    AND id<>$2 AND metadata_status='ready' ORDER BY id LIMIT 1""",group_key,row["id"])
                if source:
                    await conn.execute("""UPDATE media SET title=$2,tmdb_id=$3,poster_path=$4,
                        backdrop_path=$5,overview=$6,tmdb_rating=$7,genre_id=$8,studio_id=$9,
                        language_id=$10,metadata_status='ready' WHERE id=$1""",row["id"],
                        source["title"],source["tmdb_id"],source["poster_path"],source["backdrop_path"],
                        source["overview"],source["tmdb_rating"],source["genre_id"],source["studio_id"],source["language_id"])
                    await conn.execute("""INSERT INTO media_actors(media_id,actor_id)
                        SELECT $1,actor_id FROM media_actors WHERE media_id=$2 ON CONFLICT DO NOTHING""",row["id"],source["id"])
    return {"status": "success", **dict(row), "metadata_status": status,
            "playback_status": playback_status, "media_type": kind}

class PrepareRequest(BaseModel):
    force_transcode: bool = False

@app.post("/api/catalog/{media_id}/prepare")
async def retry_preparation(media_id: int, data: PrepareRequest, user=Depends(auth.admin_user)):
    async with database.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT path,playback_status FROM media WHERE id=$1", media_id)
        if not row:
            raise HTTPException(404, "Media not found.")
        resolve_media_file(row["path"])
        await conn.execute("""UPDATE media SET playback_status='pending',prepare_progress=0,
            prepare_error=NULL,force_transcode=$2 WHERE id=$1
            AND playback_status NOT IN ('pending','preparing')""", media_id, data.force_transcode)
    return {"status": "queued"}

@app.post("/api/catalog/{media_id}/cancel")
async def cancel_preparation(media_id: int, user=Depends(auth.admin_user)):
    async with database.pool.acquire() as conn:
        row = await conn.fetchval("""UPDATE media SET playback_status='cancelled',
            prepare_error='Preparation was cancelled.' WHERE id=$1
            AND playback_status IN ('pending','preparing') RETURNING id""", media_id)
        if not row:
            raise HTTPException(409, "No active preparation to cancel.")
    return {"status": "cancelled"}

@app.delete("/api/catalog/{media_id}")
async def delete_media(media_id: int, user=Depends(auth.admin_user)):
    async with database.pool.acquire() as conn:
        result = await conn.execute("DELETE FROM media WHERE id=$1", media_id)
    if result == "DELETE 0":
        raise HTTPException(404, "Media not found.")
    return {"status": "success"}

@app.get("/api/media/{media_id}/stream")
@app.head("/api/media/{media_id}/stream")
async def stream(media_id: int, user=Depends(auth.current_user)):
    async with database.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT path,prepared_path,playback_status,prepare_error FROM media WHERE id=$1", media_id)
    if row is None:
        raise HTTPException(404, "Media not found.")
    # If the file is prepared or directly playable, serve the static file.
    try:
        return FileResponse(playback_file(row), content_disposition_type="inline")
    except HTTPException:
        pass
    # Otherwise, live-transcode on the fly.
    source = resolve_media_file(row["path"])
    try:
        info = await video_processing.inspect_video(source)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(422, str(exc))
    cmd = video_processing.live_transcode_command(source, info)
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    async def generate():
        try:
            while chunk := await process.stdout.read(65536):
                yield chunk
        finally:
            if process.returncode is None:
                process.kill()
            await process.wait()
    return StreamingResponse(generate(), media_type="video/mp4")

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class StartPlayback(StrictModel):
    media_id: int = Field(gt=0)

@app.post("/api/playback/start")
async def start_playback(data: StartPlayback, user=Depends(auth.current_user)):
    session_id = uuid.uuid4()
    async with database.pool.acquire() as conn:
        async with conn.transaction():
            file_row = await conn.fetchrow("SELECT path,prepared_path,playback_status,prepare_error FROM media WHERE id=$1 FOR SHARE", data.media_id)
            if file_row is None:
                raise HTTPException(404, "Media not found.")
            # Verify file exists (but don't require preparation — live transcode handles it).
            resolve_media_file(file_row["path"])
            await conn.execute("INSERT INTO playback_sessions(id,user_id,media_id) VALUES($1,$2,$3)",
                               session_id,user["id"],data.media_id)
            position = await conn.fetchval("""SELECT EXTRACT(EPOCH FROM last_position)
                FROM playback_state WHERE user_id=$1 AND media_id=$2""",user["id"],data.media_id)
    return {"session_id": str(session_id), "position_seconds": float(position or 0)}

class PlaybackUpdate(StrictModel):
    session_id: uuid.UUID
    sequence: int = Field(ge=0)
    position_seconds: float = Field(ge=0, le=604800, allow_inf_nan=False)

@app.post("/api/playback/update")
async def update_playback(data: PlaybackUpdate, user=Depends(auth.current_user)):
    async with database.pool.acquire() as conn:
        async with conn.transaction():
            session = await conn.fetchrow("""SELECT * FROM playback_sessions
                WHERE id=$1 AND user_id=$2 FOR UPDATE""",data.session_id,user["id"])
            if not session:
                raise HTTPException(404, "Playback session not found.")
            if session["completed"] or data.sequence <= session["last_sequence"]:
                return {"status": "ignored"}
            await conn.execute("UPDATE playback_sessions SET last_sequence=$2 WHERE id=$1",
                               data.session_id,data.sequence)
            await conn.execute("""INSERT INTO playback_state(user_id,media_id,last_position)
                VALUES($1,$2,make_interval(secs:=$3)) ON CONFLICT(user_id,media_id)
                DO UPDATE SET last_position=EXCLUDED.last_position,updated_at=NOW()""",
                user["id"],session["media_id"],data.position_seconds)
    return {"status": "success"}

class CompletePlayback(StrictModel):
    session_id: uuid.UUID

@app.post("/api/playback/complete")
async def complete_playback(data: CompletePlayback, user=Depends(auth.current_user)):
    async with database.pool.acquire() as conn:
        async with conn.transaction():
            session = await conn.fetchrow("""SELECT * FROM playback_sessions
                WHERE id=$1 AND user_id=$2 FOR UPDATE""",data.session_id,user["id"])
            if not session:
                raise HTTPException(404, "Playback session not found.")
            if not session["completed"]:
                await conn.execute("UPDATE playback_sessions SET completed=TRUE WHERE id=$1",data.session_id)
                await conn.execute("""INSERT INTO watch_history(user_id,media_id,playback_session_id)
                    VALUES($1,$2,$3)""",user["id"],session["media_id"],data.session_id)
                await conn.execute("DELETE FROM playback_state WHERE user_id=$1 AND media_id=$2",
                                   user["id"],session["media_id"])
    return {"status": "success"}

class Rating(StrictModel):
    media_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=10)

@app.post("/api/ratings")
async def rating(data: Rating, user=Depends(auth.current_user)):
    async with database.pool.acquire() as conn:
        async with conn.transaction():
            if not await conn.fetchval("SELECT id FROM media WHERE id=$1 FOR SHARE",data.media_id):
                raise HTTPException(404, "Media not found.")
            await conn.execute("""INSERT INTO ratings(user_id,media_id,rating) VALUES($1,$2,$3)
                ON CONFLICT(user_id,media_id) DO UPDATE SET rating=EXCLUDED.rating,created_at=NOW()""",
                user["id"],data.media_id,data.rating)
    return {"status": "success"}

@app.get("/api/{path:path}", include_in_schema=False)
async def missing_api(path: str):
    raise HTTPException(404, "API endpoint not found.")

dist = ROOT / "frontend" / "dist"
if dist.is_dir():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
