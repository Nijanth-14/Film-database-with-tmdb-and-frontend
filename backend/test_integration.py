"""Integration tests use a disposable PostgreSQL database and temporary media folder."""
import asyncio
import os
import tempfile
import subprocess
import shutil
import unittest
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
from settings import DATABASE_URL

original_url = DATABASE_URL
test_name = "stream_test_" + uuid.uuid4().hex[:12]
parts = urlsplit(original_url)
# Preserve the triple slash for a local-socket PostgreSQL URL.
test_url = urlunsplit(parts._replace(path="/" + test_name))
if not parts.netloc:
    test_url = "postgresql:///" + test_name
test_media = tempfile.TemporaryDirectory(prefix="stream-test-")
os.environ["DATABASE_URL"] = test_url
os.environ["MEDIA_ROOT"] = test_media.name
os.environ["TMDB_API_KEY"] = ""
os.environ["MEDIA_IMPORT_ROOTS"] = ""
os.environ["PREPARATION_WORKER_ENABLED"] = "false"

# settings was imported to discover the configured DB; override before app imports.
import settings
settings.DATABASE_URL = test_url
settings.MEDIA_ROOT = Path(test_media.name)
settings.MEDIA_CACHE_ROOT = Path(test_media.name) / ".prepared"

async def create_database():
    conn = await asyncpg.connect(original_url)
    try:
        await conn.execute(f'CREATE DATABASE "{test_name}"')
    finally:
        await conn.close()

async def drop_database():
    assert test_name.startswith("stream_test_") and len(test_name) == 24
    conn = await asyncpg.connect(original_url)
    try:
        await conn.execute(f'DROP DATABASE "{test_name}"')
    finally:
        await conn.close()

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from main import app
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls.client.post("/api/auth/register", json={"username":"admin_test","password":"test-password-123"})
        cls.admin_cookie = dict(cls.client.cookies)
        cls.client.post("/api/auth/register", json={"username":"viewer_test","password":"test-password-123"})
        cls.viewer_cookie = dict(cls.client.cookies)
        cls.client.cookies.clear()
        cls.client.cookies.update(cls.admin_cookie)
        from video_processing import ffmpeg_executable
        subprocess.run([ffmpeg_executable(), "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=2",
            "-t", "70", "-c:v", "libvpx", str(Path(test_media.name,"test.webm"))], check=True)
        cls.media_id = cls.client.post("/api/catalog", json={
            "title":"Conference Video", "path":"test.webm", "duration_seconds":60}).json()["id"]

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def setUp(self):
        import auth
        auth.attempts.clear()
        self.client.cookies.clear()
        self.client.cookies.update(self.admin_cookie)

    def test_distinct_actor_ids_may_share_a_name(self):
        import database
        async def verify():
            async with database.pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute("INSERT INTO actors(name,tmdb_id) VALUES('Same Name',100001),('Same Name',100002)")
                    return await conn.fetchval("SELECT COUNT(*) FROM actors WHERE name='Same Name'")
        self.assertEqual(self.client.portal.call(verify),2)

    def test_health_and_fresh_schema(self):
        self.assertEqual(self.client.get("/api/health").status_code,200)
        self.assertTrue(self.client.get("/api/auth/me").json()["is_admin"])

    def test_auth_required_and_logout_revokes_cookie(self):
        self.client.cookies.clear()
        result = self.client.post("/api/auth/login",json={"username":"admin_test","password":"test-password-123"})
        self.assertEqual(result.status_code,200)
        saved = dict(self.client.cookies)
        self.assertIn("HttpOnly",result.headers["set-cookie"])
        self.client.post("/api/auth/logout")
        self.client.cookies.update(saved)
        self.assertEqual(self.client.get("/api/catalog").status_code,401)
        self.client.cookies.clear()
        self.assertEqual(self.client.get(f"/api/media/{self.media_id}/stream").status_code,401)

    def test_wrong_password_and_validation(self):
        self.assertEqual(self.client.post("/api/auth/login",json={
            "username":"admin_test","password":"incorrect-password"}).status_code,401)
        self.assertEqual(self.client.post("/api/auth/register",json={
            "username":"new_user","password":"short"}).status_code,422)

    def test_viewer_cannot_modify_catalog(self):
        self.client.cookies.clear()
        self.client.cookies.update(self.viewer_cookie)
        self.assertFalse(self.client.get("/api/auth/me").json()["is_admin"])
        self.assertEqual(self.client.delete(f"/api/catalog/{self.media_id}").status_code,403)
        self.assertEqual(self.client.post("/api/catalog",json={"path":"test.webm"}).status_code,403)

    def test_origin_protection(self):
        self.assertEqual(self.client.post("/api/auth/logout",
            headers={"Origin":"https://attacker.example"}).status_code,403)

    def test_file_confinement_missing_duplicate_and_range(self):
        self.assertEqual(self.client.post("/api/catalog",json={"path":"../escape.mp4"}).status_code,400)
        self.assertEqual(self.client.post("/api/catalog",json={"path":"missing.webm"}).status_code,404)
        self.assertEqual(self.client.post("/api/catalog",json={"path":"test.webm"}).status_code,409)
        response = self.client.get(f"/api/media/{self.media_id}/stream",headers={"Range":"bytes=0-99"})
        self.assertEqual(response.status_code,206)
        self.assertEqual(len(response.content),100)
        self.assertEqual(response.headers["content-range"],f"bytes 0-99/{Path(test_media.name,'test.webm').stat().st_size}")
        self.assertEqual(self.client.get(f"/api/media/{self.media_id}/stream",
            headers={"Range":"bytes=999999999-1000000000"}).status_code,416)

    def test_symlinks_cannot_escape_media_root(self):
        outside = Path(test_media.name).parent / (test_name + ".mp4")
        outside.write_bytes(b"private")
        link = Path(test_media.name) / "escape.mp4"
        try:
            link.symlink_to(outside)
            self.assertEqual(self.client.post("/api/catalog",json={"path":"escape.mp4"}).status_code,400)
        finally:
            link.unlink()
            outside.unlink()

    def test_catalog_search_pagination_and_detail(self):
        for i in range(3):
            shutil.copyfile(Path(test_media.name,"test.webm"),Path(test_media.name,f"page{i}.webm"))
            self.client.post("/api/catalog",json={"path":f"page{i}.webm","title":f"Pagination Test {i}"})
        first = self.client.get("/api/catalog",params={"limit":2}).json()
        self.assertEqual(len(first["items"]),2)
        second = self.client.get("/api/catalog",params={"limit":2,"after":first["next_cursor"]}).json()
        self.assertFalse({x["id"] for x in first["items"]} & {x["id"] for x in second["items"]})
        found = self.client.get("/api/catalog",params={"q":"Confer"}).json()["items"]
        self.assertEqual(found[0]["id"],self.media_id)
        self.assertNotIn("path",found[0])
        self.assertTrue(self.client.get(f"/api/catalog/{self.media_id}").json()["available"])
        self.assertEqual(self.client.get("/api/catalog?limit=1000").status_code,422)

    def test_playback_resume_stale_updates_and_duplicate_completion(self):
        session = self.client.post("/api/playback/start",json={"media_id":self.media_id}).json()["session_id"]
        update = {"session_id":session,"sequence":2,"position_seconds":25}
        self.assertEqual(self.client.post("/api/playback/update",json=update).status_code,200)
        stale = dict(update,sequence=1,position_seconds=5)
        self.assertEqual(self.client.post("/api/playback/update",json=stale).json()["status"],"ignored")
        resumed = self.client.post("/api/playback/start",json={"media_id":self.media_id}).json()
        self.assertEqual(resumed["position_seconds"],25)
        self.assertEqual(self.client.post("/api/playback/update",
            json=dict(update,position_seconds=-1)).status_code,422)
        self.assertEqual(self.client.post("/api/playback/update",
            json=dict(update,user_id=999)).status_code,422)
        self.client.cookies.clear()
        self.client.cookies.update(self.viewer_cookie)
        self.assertEqual(self.client.get("/api/dashboard").json(),[])
        self.assertEqual(self.client.post("/api/playback/update",json=update).status_code,404)
        self.client.cookies.clear()
        self.client.cookies.update(self.admin_cookie)
        before = next(x["view_count"] for x in self.client.get("/api/trending").json() if x["id"]==self.media_id)
        for _ in range(2):
            self.assertEqual(self.client.post("/api/playback/complete",json={"session_id":session}).status_code,200)
        self.assertEqual(self.client.post("/api/playback/update",json=dict(update,sequence=3)).json()["status"],"ignored")
        after = next(x["view_count"] for x in self.client.get("/api/trending").json() if x["id"]==self.media_id)
        self.assertEqual(after,before+1)
        self.assertFalse(any(x["id"]==self.media_id for x in self.client.get("/api/dashboard").json()))

    def test_full_movie_preparation_preserves_more_than_sixty_seconds(self):
        from video_processing import ffmpeg_executable, inspect_video, run_next
        import database
        source = Path(test_media.name,"Full.Movie.2025.mkv")
        subprocess.run([ffmpeg_executable(), "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=2",
            "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=8000",
            "-t", "70", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", str(source)], check=True)
        response = self.client.post("/api/catalog",json={"path":source.name})
        self.assertEqual(response.status_code,201,response.text)
        data=response.json()
        self.assertEqual(data["media_type"],"movie")
        self.assertEqual(data["playback_status"],"pending")
        media_id=data["id"]
        self.assertEqual(self.client.post("/api/playback/start",json={"media_id":media_id}).status_code,200)
        live=self.client.get(f"/api/media/{media_id}/stream")
        self.assertEqual(live.status_code,200)
        self.assertIn(b"ftyp",live.content[:32])
        async def prepare_one():
            async with database.pool.acquire() as conn:
                self.assertTrue(await run_next(conn))
        self.client.portal.call(prepare_one)
        detail=self.client.get(f"/api/catalog/{media_id}").json()
        self.assertEqual(detail["playback_status"],"ready",detail)
        self.assertGreater(detail["duration"],69)
        output=settings.MEDIA_CACHE_ROOT / f"{media_id}.mp4"
        info=asyncio.run(inspect_video(output))
        self.assertGreater(info["duration_seconds"],69)
        self.assertEqual(info["audio_codec"],"aac")
        self.assertTrue(source.is_file())
        response=self.client.get(f"/api/media/{media_id}/stream",headers={"Range":"bytes=0-99"})
        self.assertEqual(response.status_code,206)
        # Decode near the END, past 60s, proving the prepared copy is not a short clip.
        subprocess.run([ffmpeg_executable(), "-hide_banner", "-loglevel", "error",
            "-ss","65","-i",str(output),"-frames:v","1","-f","null","-"],check=True)

    def test_import_autodetection_and_invalid_video(self):
        from video_processing import detect_identity
        episode=Path(test_media.name,"Example.Show.S02E03.1080p.webm")
        shutil.copyfile(Path(test_media.name,"test.webm"),episode)
        result=self.client.post("/api/import/inspect",json={"path":episode.name})
        self.assertEqual(result.status_code,200,result.text)
        data=result.json()
        self.assertEqual(data["media_type"],"tv")
        self.assertEqual((data["season_number"],data["episode_number"]),(2,3))
        self.assertGreater(data["duration_seconds"],69)
        created=self.client.post("/api/catalog",json={"path":episode.name}).json()
        self.assertEqual(created["media_type"],"tv")
        movie=detect_identity("Demon Slayer - Kimetsu No Yaiba Infinity Castle (2025) 1080p BluRay x264.mkv")
        self.assertEqual(movie["media_type"],"movie")
        self.assertEqual(movie["release_year"],2025)
        self.assertIn("Infinity Castle",movie["title"])
        invalid=Path(test_media.name,"broken.mkv")
        invalid.write_bytes(b"not a video")
        self.assertEqual(self.client.post("/api/catalog",json={"path":invalid.name}).status_code,422)

    def test_preparation_cancel_retry_and_viewer_restrictions(self):
        media_id=self.media_id
        self.assertEqual(self.client.post(f"/api/catalog/{media_id}/prepare",json={}).status_code,200)
        self.assertEqual(self.client.post(f"/api/catalog/{media_id}/cancel").status_code,200)
        self.assertEqual(self.client.get(f"/api/catalog/{media_id}").json()["playback_status"],"cancelled")
        self.client.cookies.clear()
        self.client.cookies.update(self.viewer_cookie)
        self.assertEqual(self.client.post(f"/api/catalog/{media_id}/prepare",json={}).status_code,403)
        self.client.cookies.clear()
        self.client.cookies.update(self.admin_cookie)
        self.assertEqual(self.client.post(f"/api/catalog/{media_id}/prepare",json={}).status_code,200)
        from video_processing import run_next
        import database
        async def retry_one():
            async with database.pool.acquire() as conn:
                await run_next(conn)
        self.client.portal.call(retry_one)
        detail=self.client.get(f"/api/catalog/{media_id}").json()
        self.assertEqual(detail["playback_status"],"ready",detail)

    def test_metadata_restores_complete_details_and_replaces_cast(self):
        import metadata, database, httpx
        requests=[]
        def respond(request):
            requests.append(request.url.path)
            if "/search/" in request.url.path:
                return httpx.Response(200,json={"results":[{"id":123,"title":"Restored Film"}]})
            return httpx.Response(200,json={"id":123,"title":"Restored Film",
                "poster_path":"/cover.jpg","backdrop_path":"/background.jpg",
                "overview":"A complete synopsis.","vote_average":8.4,
                "genres":[{"name":"Drama"}],"production_companies":[{"name":"Test Studio"}],
                "original_language":"en","spoken_languages":[{"iso_639_1":"en","english_name":"English"}],
                "credits":{"cast":[{"id":456,"name":"Test Performer"}]}})
        async def enrich():
            async with httpx.AsyncClient(base_url=metadata.BASE_URL,transport=httpx.MockTransport(respond)) as client:
                await metadata.enrich({"id":self.media_id,"title":"Restored Film","media_type":"movie"},client,"test")
                await metadata.save_details(self.media_id,"movie",123,client,"test")
        self.client.portal.call(enrich)
        item=self.client.get(f"/api/catalog/{self.media_id}").json()
        self.assertEqual(item["poster_path"],"/cover.jpg")
        self.assertEqual(item["backdrop_path"],"/background.jpg")
        self.assertEqual(item["overview"],"A complete synopsis.")
        self.assertEqual(item["tmdb_rating"],8.4)
        self.assertEqual(item["actors"],["Test Performer"])
        self.assertEqual(item["studio"],"Test Studio")
        self.assertEqual(item["language"],"English")
        self.assertEqual(item["metadata_status"],"ready")

    def test_file_picker_and_hidden_extension_resolution(self):
        from media_files import resolve_media_file
        name="Movie.2025 [Audio 2.0 + 5.1]"
        source=Path(test_media.name,name+".MKV")
        source.write_bytes(b"fixture for path resolution only")
        self.assertEqual(resolve_media_file(name),source)
        self.assertEqual(resolve_media_file('"'+str(source)+'"'),source)
        response=self.client.get("/api/import/files")
        self.assertEqual(response.status_code,200)
        self.assertTrue(any(x["path"]==str(source) for x in response.json()))
        second=Path(test_media.name,name+".mp4")
        second.write_bytes(b"ambiguous")
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as error:
            resolve_media_file(name)
        self.assertEqual(error.exception.status_code,409)
        self.client.cookies.clear()
        self.client.cookies.update(self.viewer_cookie)
        self.assertEqual(self.client.get("/api/import/files").status_code,403)
        self.assertEqual(self.client.get("/api/metadata/search?q=Movie").status_code,403)
        self.assertEqual(self.client.post(f"/api/catalog/{self.media_id}/metadata",
            json={"tmdb_id":123,"media_type":"movie"}).status_code,403)

    def test_rating_validation_and_missing_media(self):
        self.assertEqual(self.client.post("/api/ratings",json={"media_id":self.media_id,"rating":11}).status_code,422)
        self.assertEqual(self.client.post("/api/ratings",json={"media_id":self.media_id,"rating":8}).status_code,200)
        self.assertEqual(self.client.get(f"/api/catalog/{self.media_id}").json()["rating"],8)
        self.assertEqual(self.client.delete("/api/catalog/999999").status_code,404)

if __name__ == "__main__":
    asyncio.run(create_database())
    try:
        async def confirm_isolation():
            conn = await asyncpg.connect(test_url)
            try:
                actual = await conn.fetchval("SELECT current_database()")
                if actual != test_name:
                    raise RuntimeError("Refusing tests: connection is not the disposable database.")
            finally:
                await conn.close()
        asyncio.run(confirm_isolation())
        from setup_db import setup
        asyncio.run(setup())
        asyncio.run(setup())  # Migration reruns must be safe.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(IntegrationTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        asyncio.run(drop_database())
        test_media.cleanup()
    raise SystemExit(0 if result.wasSuccessful() else 1)
