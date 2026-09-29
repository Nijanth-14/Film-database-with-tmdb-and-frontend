"""Inspect codecs and prepare browser-compatible media with a durable, serialized queue."""
import asyncio
import logging
import os
import re
import shutil
import uuid
from contextlib import suppress
from pathlib import Path
import asyncpg
import guessit
from fastapi import HTTPException
from settings import DATABASE_URL, MEDIA_CACHE_ROOT
from media_files import resolve_media_file

log = logging.getLogger(__name__)

def ffmpeg_executable():
    # Prefer system FFmpeg — it is far more likely to include hardware encoder support.
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        raise RuntimeError("Video preparation is unavailable. Install backend requirements and restart.")

_hw_encoder_cache = None

def _detect_hw_encoder():
    """Probe once for a hardware h264 encoder by attempting a real 1-frame encode."""
    global _hw_encoder_cache
    if _hw_encoder_cache is not None:
        return _hw_encoder_cache
    import subprocess
    exe = ffmpeg_executable()
    # Ordered by typical speed / quality trade-off.
    candidates = [
        ("h264_qsv",  ["-c:v", "h264_qsv", "-preset", "veryfast", "-global_quality", "25"]),
        ("h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "25", "-b:v", "0"]),
        ("h264_vaapi", ["-vaapi_device", "/dev/dri/renderD128",
                        "-c:v", "h264_vaapi", "-qp", "25",
                        "-vf", "format=nv12|vaapi,hwupload"]),
    ]
    for name, args in candidates:
        try:
            # Encode one black frame — proves the device and encoder actually work.
            cmd = [exe, "-hide_banner", "-loglevel", "error",
                   "-f", "lavfi", "-i", "color=black:s=64x64:d=0.04",
                   *args, "-frames:v", "1", "-f", "null", "-"]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=10, check=True)
            _hw_encoder_cache = tuple(args)
            log.info("Hardware encoder available and verified: %s", name)
            return _hw_encoder_cache
        except Exception:
            log.debug("Hardware encoder %s not usable, skipping.", name)
    _hw_encoder_cache = ()
    log.info("No hardware encoder available; using software encoding.")
    return _hw_encoder_cache

def detect_identity(path):
    guessed = guessit.guessit(Path(path).name)
    folder=Path(path).parent
    season_folder=re.fullmatch(r"(?:season[ ._-]*|s)(\d+)",folder.name,re.I)
    if season_folder:
        guessed.setdefault("season",int(season_folder[1]))
        if not guessed.get("episode"):
            match=re.match(r"^(?:e(?:pisode)?[ ._-]*)?(\d{1,3})(?:[ ._-]|$)",Path(path).stem,re.I)
            if match:
                guessed["episode"]=int(match[1])
    if "season" in guessed or "episode" in guessed:
        if not guessed.get("title"):
            guessed["title"]=folder.parent.name if season_folder else folder.name
    kind = "tv" if guessed.get("type") == "episode" or "episode" in guessed or "season" in guessed else "movie"
    def number(value):
        if isinstance(value, list):
            value = value[0] if value else None
        return int(value) if value is not None else None
    title = str(guessed.get("title") or Path(path).stem)
    alternative = guessed.get("alternative_title")
    if kind == "movie" and alternative:
        title += " - " + (" - ".join(map(str, alternative)) if isinstance(alternative, list) else str(alternative))
    return {"title": title,
            "media_type": kind, "season_number": number(guessed.get("season")),
            "episode_number": number(guessed.get("episode")), "release_year": number(guessed.get("year"))}

async def inspect_video(path):
    # "-i" without an output reads headers and exits; it does not transcode the source.
    process = await asyncio.create_subprocess_exec(ffmpeg_executable(), "-hide_banner", "-i", str(path),
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
    try:
        _, error = await asyncio.wait_for(process.communicate(), timeout=30)
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise
    info = error.decode(errors="replace")
    video = next((line for line in info.splitlines() if "Video:" in line and "(attached pic)" not in line), "")
    audio = next((line for line in info.splitlines() if "Audio:" in line), "")
    codec = re.search(r"Video:\s*(\w+)", video)
    audio_codec = re.search(r"Audio:\s*(\w+)", audio)
    duration = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", info)
    if not codec or not duration:
        raise ValueError("Could not read this video. The file may be incomplete, damaged or unsupported.")
    seconds = int(duration[1])*3600 + int(duration[2])*60 + float(duration[3])
    if seconds <= 0:
        raise ValueError("This video has no readable duration.")
    video_codec, sound = codec[1], audio_codec[1] if audio_codec else None
    h264 = video_codec == "h264" and bool(re.search(r"\byuv420p\b", video))
    suffix = Path(path).suffix.lower()
    direct = (suffix in {".mp4", ".m4v"} and h264 and sound in {None, "aac", "mp3"}) or (
        suffix == ".webm" and video_codec in {"vp8", "vp9", "av1"} and sound in {None, "opus", "vorbis"}) or (
        suffix in {".ogg", ".ogv"} and video_codec == "theora" and sound in {None, "vorbis", "opus"})
    return {"duration_seconds": seconds, "video_codec": video_codec, "audio_codec": sound,
            "copy_video": h264, "direct": direct}

def live_transcode_command(source, info, start_seconds=0):
    """Build an FFmpeg command that transcodes to fragmented MP4 on stdout for live streaming."""
    exe = ffmpeg_executable()
    command = [exe, "-hide_banner", "-loglevel", "error", "-nostdin"]
    if start_seconds > 0:
        command += ["-ss", str(start_seconds)]
    command += ["-i", str(source), "-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn"]
    if info["copy_video"]:
        command += ["-c:v", "copy"]
    else:
        hw = _detect_hw_encoder()
        if hw:
            hw = list(hw)
            if "h264_vaapi" in hw:
                idx = hw.index("-vf")
                hw[idx + 1] = f"{SCALE_FILTER},format=nv12|vaapi,hwupload"
                command += hw
            else:
                command += ["-vf", SCALE_FILTER, "-pix_fmt", "yuv420p"] + hw
        else:
            command += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                        "-threads", "0",
                        "-vf", SCALE_FILTER, "-pix_fmt", "yuv420p",
                        "-maxrate", "4M", "-bufsize", "8M"]
    command += (["-c:a", "copy"] if info["audio_codec"] == "aac" else
                ["-c:a", "aac", "-b:a", "160k", "-ac", "2"])
    # Fragmented MP4: streamable without seeking back to patch the header.
    command += ["-movflags", "frag_keyframe+empty_moov+default_base_moof",
                "-f", "mp4", "pipe:1"]
    return command

SCALE_FILTER = "scale=-2:trunc(min(720\\,ih)/2)*2"

def conversion_command(source, output, info, force=False):
    copy = info["copy_video"] and not force
    command = [ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
               "-i", str(source), "-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn"]
    if copy:
        command += ["-c:v", "copy"]
    else:
        hw = _detect_hw_encoder()
        if hw:
            # Hardware path — insert encoder args; add software scale before any hw filter.
            hw = list(hw)
            if "h264_vaapi" in hw:
                # VAAPI needs scale before hwupload; replace the detect-provided -vf.
                idx = hw.index("-vf")
                hw[idx + 1] = f"{SCALE_FILTER},format=nv12|vaapi,hwupload"
                command += hw
            else:
                command += ["-vf", SCALE_FILTER, "-pix_fmt", "yuv420p"] + hw
        else:
            command += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                        "-threads", "0",
                        "-vf", SCALE_FILTER, "-pix_fmt", "yuv420p",
                        "-maxrate", "4M", "-bufsize", "8M"]
    command += (["-c:a", "copy"] if info["audio_codec"] == "aac" else
                ["-c:a", "aac", "-b:a", "160k", "-ac", "2"])
    return command + ["-movflags", "+faststart", "-progress", "pipe:1", "-stats_period", "1", str(output)]

async def prepare(conn, row):
    MEDIA_CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    temporary = MEDIA_CACHE_ROOT / f"{row['id']}-{uuid.uuid4().hex}.part.mp4"
    final = MEDIA_CACHE_ROOT / f"{row['id']}.mp4"
    process = None
    stderr_task = None
    try:
        source = resolve_media_file(row["path"])
        info = await inspect_video(source)
        # Copying video preserves its size; encoding has a bounded target bitrate.
        estimate = source.stat().st_size if info["copy_video"] and not row["force_transcode"] else info["duration_seconds"]*550000
        if shutil.disk_usage(MEDIA_CACHE_ROOT).free < estimate*1.1 + 100_000_000:
            raise ValueError("Not enough free disk space to prepare this video. Free space and select Retry.")
        process = await asyncio.create_subprocess_exec(*conversion_command(source, temporary, info, row["force_transcode"]),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        async def read_error():
            tail = b""
            while chunk := await process.stderr.read(4096):
                tail = (tail + chunk)[-16000:]
            return tail.decode(errors="replace")
        stderr_task = asyncio.create_task(read_error())
        while True:
            try:
                line = await asyncio.wait_for(process.stdout.readline(), timeout=2)
            except asyncio.TimeoutError:
                line = None
            status = await conn.fetchval("SELECT playback_status FROM media WHERE id=$1", row["id"])
            if status != "preparing":
                return  # Deletion or explicit cancellation: finally terminates FFmpeg.
            if line == b"":
                break
            if line and line.startswith(b"out_time_us="):
                try:
                    percent = min(99.0, max(0, int(line.split(b"=")[1])/1_000_000/info["duration_seconds"]*100))
                    await conn.execute("UPDATE media SET prepare_progress=$2 WHERE id=$1", row["id"], percent)
                except ValueError:
                    pass
        await process.wait()
        error = await stderr_task
        if process.returncode != 0:
            log.warning("FFmpeg failed for media %s: %s", row["id"], error[-2000:])
            raise ValueError("Video preparation failed. Check free disk space and the source file, then retry.")
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise ValueError("Video preparation produced no playable output.")
        # Publish only a completed file; never serve partial MP4s.
        async with conn.transaction():
            status = await conn.fetchval("SELECT playback_status FROM media WHERE id=$1 FOR UPDATE", row["id"])
            if status != "preparing":
                return
            temporary.replace(final)
            await conn.execute("""UPDATE media SET playback_status='ready',prepared_path=$2,
                prepare_progress=100,prepare_error=NULL,duration=make_interval(secs:=$3) WHERE id=$1""",
                row["id"], final.name, info["duration_seconds"])
    except asyncio.CancelledError:
        await conn.execute("""UPDATE media SET playback_status='pending',prepare_progress=0
            WHERE id=$1 AND playback_status='preparing'""", row["id"])
        raise
    except Exception as exc:
        message = exc.detail if isinstance(exc, HTTPException) else str(exc)
        await conn.execute("""UPDATE media SET playback_status='failed',prepare_error=$2
            WHERE id=$1 AND playback_status='preparing'""", row["id"], message[:500])
    finally:
        if process and process.returncode is None:
            with suppress(ProcessLookupError):
                process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        if stderr_task:
            await stderr_task
        temporary.unlink(missing_ok=True)

async def run_next(conn):
    row = await conn.fetchrow("""UPDATE media SET playback_status='preparing',prepare_error=NULL,
        prepare_progress=0 WHERE id=(SELECT id FROM media WHERE playback_status='pending'
        ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *""")
    if row:
        await prepare(conn, row)
    return bool(row)

async def worker():
    # Dedicated connection + advisory lock serialize expensive jobs across API workers.
    if os.getenv("PREPARATION_WORKER_ENABLED", "true").lower() != "true":
        return
    while True:
        conn = None
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            if not await conn.fetchval("SELECT pg_try_advisory_lock(7192030)"):
                await conn.close()
                conn = None
                await asyncio.sleep(3)
                continue
            # A previous worker crashed while holding the lock; safely requeue unfinished jobs.
            await conn.execute("UPDATE media SET playback_status='pending' WHERE playback_status='preparing'")
            while True:
                if not await run_next(conn):
                    await asyncio.sleep(2)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Video worker failed; reconnecting.")
            await asyncio.sleep(5)
        finally:
            if conn and not conn.is_closed():
                await conn.close()
