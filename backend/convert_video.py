"""Create a browser-compatible full video; clipping is only enabled by explicit arguments."""
import argparse
import shutil
import subprocess
from pathlib import Path
from settings import MEDIA_ROOT

parser = argparse.ArgumentParser(description="Optional converter: preserves the full duration by default. The app prepares imports automatically.")
parser.add_argument("source", type=Path, help="Full Linux/WSL path to the source video")
parser.add_argument("--name", default="browser-video.mp4", help="Output filename inside MEDIA_ROOT")
parser.add_argument("--start", type=int, default=0)
parser.add_argument("--seconds", type=int, default=None, help="Optional clip length; omitted means the entire remaining video")
args = parser.parse_args()
if not args.source.is_file():
    parser.error("Source file does not exist.")
if (args.seconds is not None and args.seconds < 1) or args.start < 0:
    parser.error("Use a positive duration and non-negative start time.")
target = (MEDIA_ROOT / args.name).resolve()
if not target.is_relative_to(MEDIA_ROOT) or target.suffix.lower() != ".mp4":
    parser.error("Output must be an MP4 inside MEDIA_ROOT.")
if target.exists():
    parser.error("Output already exists; choose another --name. Nothing was overwritten.")
ffmpeg = shutil.which("ffmpeg")
if not ffmpeg:
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        parser.error("Install FFmpeg or run: backend/venv/bin/pip install imageio-ffmpeg==0.6.0")
target.parent.mkdir(parents=True, exist_ok=True)
command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-n",
    "-ss", str(args.start), "-i", str(args.source),
    *([] if args.seconds is None else ["-t", str(args.seconds)]),
    "-map", "0:v:0", "-map", "0:a:0?", "-vf", "scale=-2:720",
    "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ac", "2",
    "-movflags", "+faststart", str(target)]
subprocess.run(command, check=True)
print("Video created:", target)
