"""Resolve only configured local libraries; accept Windows paths when running in WSL."""
import os
import re
from pathlib import Path
from fastapi import HTTPException
from settings import MEDIA_ROOT, MEDIA_CACHE_ROOT

EXTENSIONS = {".mp4", ".m4v", ".mkv", ".webm", ".ogg", ".ogv", ".mov", ".avi", ".ts", ".m2ts", ".wmv"}

def local_path(value: str) -> Path:
    value = value.strip().strip('"').strip("'")
    if os.name != "nt" and re.match(r"^[A-Za-z]:[\\/]", value):
        value = "/mnt/" + value[0].lower() + "/" + value[3:].replace("\\", "/")
    return Path(value).expanduser()

def library_roots():
    extras = os.getenv("MEDIA_IMPORT_ROOTS", "")
    return [MEDIA_ROOT, *[local_path(p).resolve() for p in extras.split(";") if p.strip()]]

def resolve_media_file(value: str) -> Path:
    requested = local_path(value)
    roots = library_roots()
    candidates = [requested] if requested.is_absolute() else [root / requested for root in roots]
    allowed = [p for p in candidates if any(p.resolve().is_relative_to(root) for root in roots)]
    if not allowed:
        raise HTTPException(400, "File is outside your configured media folders.")
    matches = set()
    unsupported = False
    for candidate in allowed:
        if candidate.is_file():
            if candidate.suffix.lower() in EXTENSIONS:
                matches.add(candidate.resolve())
            else:
                unsupported = True
            continue
        # Windows Explorer may hide the extension; match exact stems, never fuzzy/glob names.
        if candidate.parent.is_dir():
            for entry in candidate.parent.iterdir():
                if entry.suffix.lower() in EXTENSIONS and (
                    entry.stem.casefold()==candidate.name.casefold() or entry.name.casefold()==candidate.name.casefold()
                ) and entry.is_file():
                    resolved = entry.resolve()
                    if not any(resolved.is_relative_to(root) for root in roots):
                        raise HTTPException(400, "File points outside your configured media folders.")
                    matches.add(resolved)
    if len(matches)>1:
        raise HTTPException(409, "Multiple videos match this name. Choose the file from the library picker.")
    if matches:
        return matches.pop()
    if unsupported:
        raise HTTPException(400, "This file is not a supported video. Choose a video from the library picker.")
    raise HTTPException(404, "Video not found. Choose it from the library picker or paste its complete path.")

def list_import_files(query=""):
    items=[]
    seen=set()
    for root in library_roots():
        if not root.is_dir():
            continue
        for entry in root.iterdir():
            if entry.suffix.lower() not in EXTENSIONS or query.casefold() not in entry.name.casefold():
                continue
            try:
                path=resolve_media_file(str(entry))
                if path in seen:
                    continue
                seen.add(path)
                items.append({"name":entry.name,"path":str(path),"folder":str(root)})
            except (HTTPException,OSError):
                continue
            if len(items)>=200:
                return items
    return sorted(items,key=lambda x:x["name"].casefold())


def playback_file(row):
    if row["playback_status"] != "ready":
        raise HTTPException(409, row["prepare_error"] or "This video is still being prepared for playback.")
    if row["prepared_path"]:
        path = (MEDIA_CACHE_ROOT / row["prepared_path"]).resolve()
        if not path.is_relative_to(MEDIA_CACHE_ROOT) or not path.is_file():
            raise HTTPException(404, "Prepared video is missing. Ask the administrator to prepare it again.")
        return path
    return resolve_media_file(row["path"])


def resolve_import_folder(value: str):
    """Recognize directories without bypassing the configured library boundary."""
    requested = local_path(value)
    roots = library_roots()
    candidates = [requested] if requested.is_absolute() else [root / requested for root in roots]
    matches = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if candidate.is_dir():
            if not any(resolved.is_relative_to(root) for root in roots):
                raise HTTPException(400, "Folder is outside your configured media libraries.")
            matches.add(resolved)
    if len(matches) > 1:
        raise HTTPException(409, "Multiple folders match this name. Paste the full folder path.")
    return matches.pop() if matches else None
