import os
from pathlib import Path
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / "backend" / ".env")
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT", str(ROOT / "media"))).expanduser().resolve()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql:///multimedia_db")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

MEDIA_CACHE_ROOT = Path(os.getenv("MEDIA_CACHE_ROOT", str(ROOT / "media" / ".prepared"))).expanduser().resolve()
