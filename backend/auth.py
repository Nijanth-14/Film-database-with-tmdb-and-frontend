"""Scrypt passwords and revocable database-backed browser sessions."""
import asyncio
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
import asyncpg
import database
from settings import COOKIE_SECURE
router = APIRouter(prefix="/api/auth")
COOKIE = "stream_session"
attempts = defaultdict(deque)

def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return f"scrypt:{salt}:{digest}"

def verify_password(password, stored):
    try:
        kind, salt, _ = stored.split(":")
        return kind == "scrypt" and hmac.compare_digest(password_hash(password, salt), stored)
    except (ValueError, TypeError):
        return False

DUMMY_HASH = password_hash(secrets.token_hex(24))

class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)

def public_user(user):
    return {key: user[key] for key in ("id", "username", "is_admin")}

def throttle(request):
    now = time.monotonic()
    key = request.client.host if request.client else "unknown"
    for old_key in list(attempts):
        if not attempts[old_key] or attempts[old_key][-1] < now - 60:
            del attempts[old_key]
    queue = attempts[key]
    while queue and queue[0] < now - 60:
        queue.popleft()
    if len(queue) >= 15:
        raise HTTPException(429, "Too many attempts. Try again in a minute.")
    queue.append(now)

async def current_user(request: Request):
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(401, "Please sign in.")
    async with database.pool.acquire() as conn:
        user = await conn.fetchrow("""SELECT u.id,u.username,u.is_admin FROM auth_sessions s
            JOIN users u ON u.id=s.user_id WHERE s.token_hash=$1 AND s.expires_at>NOW()""",
            hashlib.sha256(token.encode()).hexdigest())
    if not user:
        raise HTTPException(401, "Session expired. Please sign in.")
    return public_user(user)

async def admin_user(user=Depends(current_user)):
    if not user["is_admin"]:
        raise HTTPException(403, "Administrator access required.")
    return user

async def new_session(conn, response, user):
    token = secrets.token_urlsafe(32)
    await conn.execute("DELETE FROM auth_sessions WHERE expires_at < NOW()")
    await conn.execute("INSERT INTO auth_sessions VALUES($1,$2,NOW()+INTERVAL '7 days')",
        hashlib.sha256(token.encode()).hexdigest(), user["id"])
    response.set_cookie(COOKIE, token, httponly=True, secure=COOKIE_SECURE,
                        samesite="strict", max_age=604800, path="/")
    return public_user(user)

@router.post("/register")
async def register(data: Credentials, request: Request, response: Response):
    throttle(request)
    hashed = await asyncio.to_thread(password_hash, data.password)
    async with database.pool.acquire() as conn:
        try:
            async with conn.transaction():
                await conn.execute("SELECT pg_advisory_xact_lock(7192027)")
                is_admin = not await conn.fetchval("SELECT EXISTS(SELECT 1 FROM users WHERE is_admin)")
                user = await conn.fetchrow("""INSERT INTO users(username,email,password_hash,is_admin)
                    VALUES($1,$2,$3,$4) RETURNING id,username,is_admin""",
                    data.username, f"{secrets.token_hex(16)}@local.invalid", hashed, is_admin)
                return await new_session(conn, response, user)
        except asyncpg.UniqueViolationError:
            raise HTTPException(409, "Username is already taken.")

@router.post("/login")
async def login(data: Credentials, request: Request, response: Response):
    throttle(request)
    async with database.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE username=$1", data.username)
    valid = await asyncio.to_thread(verify_password, data.password,
                                    user["password_hash"] if user else DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(401, "Incorrect username or password.")
    async with database.pool.acquire() as conn:
        return await new_session(conn, response, user)

@router.get("/me")
async def me(user=Depends(current_user)):
    return user

@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(COOKIE, "")
    async with database.pool.acquire() as conn:
        await conn.execute("DELETE FROM auth_sessions WHERE token_hash=$1",
                           hashlib.sha256(token.encode()).hexdigest())
    response.delete_cookie(COOKIE, path="/")
    return {"status": "success"}


@router.get("/profiles")
async def profiles(user=Depends(current_user)):
    async with database.pool.acquire() as conn:
        rows = await conn.fetch("SELECT id,username,is_admin FROM users ORDER BY lower(username),id")
    return [public_user(row) for row in rows]
