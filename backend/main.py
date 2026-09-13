from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncpg
from typing import List, Optional, Any
from contextlib import asynccontextmanager
import os
import re
import httpx
import guessit
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

import database

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect_db()
    yield
    await database.close_db()

app = FastAPI(lifespan=lifespan)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/users")
async def get_users(conn: asyncpg.Connection = Depends(database.get_db_connection)):
    users = await conn.fetch("SELECT id, username FROM users ORDER BY id")
    return [{"id": u["id"], "username": u["username"]} for u in users]

class CreateUserModel(BaseModel):
    username: str

@app.post("/api/users")
async def create_user(data: CreateUserModel, conn: asyncpg.Connection = Depends(database.get_db_connection)):
    if not data.username or not data.username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    
    import uuid
    dummy_email = f"{data.username.strip().lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}@demo.com"
    dummy_password = "dummy_password_hash_123"
    
    query = """
        INSERT INTO users (username, email, password_hash)
        VALUES ($1, $2, $3)
        RETURNING id, username
    """
    try:
        new_user = await conn.fetchrow(query, data.username.strip(), dummy_email, dummy_password)
        return {"id": new_user["id"], "username": new_user["username"]}
    except asyncpg.exceptions.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Username already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, conn: asyncpg.Connection = Depends(database.get_db_connection)):
    query = "DELETE FROM users WHERE id = $1"
    try:
        result = await conn.execute(query, user_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="User not found")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard")
async def get_dashboard(user_id: int, conn: asyncpg.Connection = Depends(database.get_db_connection)):
    query = """
        SELECT media_id, media_title, total_duration, last_position, last_watched_at, poster_path, backdrop_path
        FROM user_dashboard
        WHERE user_id = $1
        ORDER BY last_watched_at DESC
    """
    rows = await conn.fetch(query, user_id)
    return [
        {
            "media_id": r["media_id"],
            "media_title": r["media_title"],
            "total_duration": r["total_duration"].total_seconds() if r["total_duration"] else 0,
            "last_position": r["last_position"].total_seconds() if r["last_position"] else 0,
            "last_watched_at": r["last_watched_at"].isoformat() if r["last_watched_at"] else None,
            "poster_path": r["poster_path"],
            "backdrop_path": r["backdrop_path"]
        }
        for r in rows
    ]

@app.get("/api/trending")
async def get_trending(conn: asyncpg.Connection = Depends(database.get_db_connection)):
    query = "SELECT media_id, title, poster_path, view_count FROM top_watched_media ORDER BY view_count DESC LIMIT 10"
    rows = await conn.fetch(query)
    return [dict(r) for r in rows]

@app.get("/api/catalog")
async def get_catalog(conn: asyncpg.Connection = Depends(database.get_db_connection)):
    query = """
        SELECT 
            m.id, m.title, m.duration, m.path, m.poster_path, m.backdrop_path, m.overview, m.tmdb_rating,
            g.name as genre, l.name as language, s.name as studio,
            ARRAY_AGG(a.name) as actors
        FROM media m
        LEFT JOIN genres g ON m.genre_id = g.id
        LEFT JOIN languages l ON m.language_id = l.id
        LEFT JOIN studios s ON m.studio_id = s.id
        LEFT JOIN media_actors ma ON m.id = ma.media_id
        LEFT JOIN actors a ON ma.actor_id = a.id
        GROUP BY m.id, g.name, l.name, s.name
        ORDER BY m.id
    """
    rows = await conn.fetch(query)
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "duration": r["duration"].total_seconds() if r["duration"] else 0,
            "path": r["path"],
            "poster_path": r["poster_path"],
            "backdrop_path": r["backdrop_path"],
            "overview": r["overview"],
            "genre": r["genre"],
            "language": r["language"],
            "studio": r["studio"],
            "tmdb_rating": float(r["tmdb_rating"]) if r["tmdb_rating"] else None,
            "actors": r["actors"] if r["actors"] != [None] else []
        }
        for r in rows
    ]

class PlaybackUpdateModel(BaseModel):
    user_id: int
    media_id: int
    position_seconds: float 

@app.post("/api/playback/update")
async def update_playback(data: PlaybackUpdateModel, conn: asyncpg.Connection = Depends(database.get_db_connection)):
    query = """
        INSERT INTO playback_state (user_id, media_id, last_position, updated_at)
        VALUES ($1, $2, make_interval(secs := $3), NOW())
        ON CONFLICT (user_id, media_id)
        DO UPDATE SET last_position = EXCLUDED.last_position, updated_at = NOW()
    """
    try:
        await conn.execute(query, data.user_id, data.media_id, data.position_seconds)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PlaybackCompleteModel(BaseModel):
    user_id: int
    media_id: int

@app.post("/api/playback/complete")
async def complete_playback(data: PlaybackCompleteModel, conn: asyncpg.Connection = Depends(database.get_db_connection)):
    query = "CALL complete_playback($1, $2)"
    try:
        await conn.execute(query, data.user_id, data.media_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RatingModel(BaseModel):
    user_id: int
    media_id: int
    rating: int

@app.post("/api/ratings")
async def submit_rating(data: RatingModel, conn: asyncpg.Connection = Depends(database.get_db_connection)):
    if not (1 <= data.rating <= 10):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 10")
    
    query = """
        INSERT INTO ratings (user_id, media_id, rating, created_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (user_id, media_id)
        DO UPDATE SET rating = EXCLUDED.rating, created_at = NOW()
    """
    try:
        await conn.execute(query, data.user_id, data.media_id, data.rating)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AddMediaModel(BaseModel):
    title: Optional[str] = None
    path: str
    duration_seconds: int = 7200 # Default 2 hours

@app.post("/api/catalog")
async def add_media(data: AddMediaModel, conn: asyncpg.Connection = Depends(database.get_db_connection)):
    tmdb_id = None
    poster_path = None
    backdrop_path = None
    overview = None
    tmdb_rating = None
    genres = []
    studios = []
    actors = []
    duration_secs = data.duration_seconds
    
    # Auto-extract title from path if not provided
    media_title = data.title
    if not media_title or not media_title.strip():
        # Normalize Windows backslashes so basename works properly
        normalized_path = data.path.replace("\\", "/")
        filename = os.path.basename(normalized_path)
        guess = guessit.guessit(filename)
        media_title = guess.get("title")
        if not media_title:
            media_title = filename

    if TMDB_API_KEY:
        async with httpx.AsyncClient() as client:
            search_type = "tv" if "episode" in data.path.lower() else "movie"
            response = await client.get(
                f"{TMDB_BASE_URL}/search/{search_type}",
                params={
                    "api_key": TMDB_API_KEY,
                    "query": media_title,
                    "page": 1,
                    "include_adult": "false"
                }
            )
            if response.status_code == 200:
                results = response.json().get("results", [])
                if results:
                    top_result = results[0]
                    tmdb_id = top_result.get("id")
                    
                    # Fetch detailed info
                    if tmdb_id:
                        detail_resp = await client.get(
                            f"{TMDB_BASE_URL}/{search_type}/{tmdb_id}",
                            params={
                                "api_key": TMDB_API_KEY,
                                "append_to_response": "credits"
                            }
                        )
                        if detail_resp.status_code == 200:
                            details = detail_resp.json()
                            poster_path = details.get("poster_path") or top_result.get("poster_path")
                            backdrop_path = details.get("backdrop_path") or top_result.get("backdrop_path")
                            overview = details.get("overview") or top_result.get("overview")
                            tmdb_rating = details.get("vote_average") or top_result.get("vote_average")
                            
                            if details.get("runtime"):
                                duration_secs = details.get("runtime") * 60
                            
                            if details.get("title"):
                                media_title = details.get("title")
                            elif details.get("name"):
                                media_title = details.get("name")
                                
                            for genre in details.get("genres", []):
                                genres.append(genre.get("name"))
                                
                            for comp in details.get("production_companies", []):
                                studios.append(comp.get("name"))
                                
                            credits = details.get("credits", {})
                            cast = credits.get("cast", [])
                            # Get top 3 actors
                            for actor in cast[:3]:
                                actors.append(actor.get("name"))
    
    try:
        async with conn.transaction():
            # Handle genre
            genre_id = None
            if genres:
                genre_id = await conn.fetchval(
                    "INSERT INTO genres (name) VALUES ($1) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                    genres[0]
                )
            
            # Handle studio
            studio_id = None
            if studios:
                studio_id = await conn.fetchval(
                    "INSERT INTO studios (name) VALUES ($1) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                    studios[0]
                )
            
            # Handle language (default English for now since TMDB returns language codes, not full names, easily)
            language_id = await conn.fetchval("SELECT id FROM languages WHERE code = 'en' LIMIT 1")
            
            query = """
                INSERT INTO media (title, duration, path, tmdb_id, poster_path, backdrop_path, overview, genre_id, studio_id, language_id, tmdb_rating)
                VALUES ($1, make_interval(secs := $2), $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id
            """
            new_id = await conn.fetchval(
                query, media_title, duration_secs, data.path, tmdb_id, poster_path, backdrop_path, overview, genre_id, studio_id, language_id, tmdb_rating
            )
            
            # Handle actors
            for actor_name in actors:
                actor_id = await conn.fetchval(
                    "INSERT INTO actors (name) VALUES ($1) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                    actor_name
                )
                await conn.execute(
                    "INSERT INTO media_actors (media_id, actor_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    new_id, actor_id
                )
                
        return {"status": "success", "id": new_id, "title": media_title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/catalog/{media_id}")
async def delete_media(media_id: int, conn: asyncpg.Connection = Depends(database.get_db_connection)):
    query = "DELETE FROM media WHERE id = $1"
    try:
        result = await conn.execute(query, media_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Media not found")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
