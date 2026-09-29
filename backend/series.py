"""Series grouping retains individual episode IDs and viewing history."""
import os
import re
from pathlib import Path
from fastapi import HTTPException
from media_files import local_path, library_roots, resolve_media_file, EXTENSIONS
from settings import MEDIA_ROOT, MEDIA_CACHE_ROOT
from video_processing import detect_identity

def series_key(title, year=None):
    normalized = "".join(c for c in title.casefold() if c.isalnum())
    return "name:" + normalized + ":" + (str(year) if year else "")

def scan_folder(value):
    folder=local_path(value)
    if not folder.is_absolute():
        folder=MEDIA_ROOT/folder
    folder=folder.resolve()
    if not any(folder.is_relative_to(root) for root in library_roots()):
        raise HTTPException(400,"Folder is outside your configured media libraries.")
    if not folder.is_dir():
        raise HTTPException(404,"Folder not found.")
    items=[]
    seen=set()
    for directory, dirs, files in os.walk(folder,followlinks=False):
        dirs[:]=sorted(d for d in dirs if not d.startswith(".") and
            not (Path(directory)/d).is_symlink() and (Path(directory)/d).resolve()!=MEDIA_CACHE_ROOT)
        for name in sorted(files):
            path=Path(directory)/name
            if path.suffix.lower() not in EXTENSIONS:
                continue
            try:
                path=resolve_media_file(str(path))
            except HTTPException:
                continue
            if path in seen:
                continue
            seen.add(path)
            items.append({"path":str(path),"filename":name,**detect_identity(path)})
            if len(items)>1000:
                raise HTTPException(413,"This folder contains over 1,000 videos. Import a smaller subfolder.")
    return items

async def get_series(conn, media_id, user_id):
    key=await conn.fetchval("""SELECT mg.group_key FROM media_library_groups mg
        JOIN media m ON m.id=mg.id WHERE m.id=$1 AND m.media_type='tv'""",media_id)
    if not key:
        raise HTTPException(404,"Series not found.")
    rows=await conn.fetch("""SELECT m.id,m.title,m.path,m.duration,m.season_number,m.episode_number,
        m.playback_status,m.prepare_progress,ps.last_position,ps.updated_at,
        EXISTS(SELECT 1 FROM watch_history wh WHERE wh.user_id=$2 AND wh.media_id=m.id) AS watched
        FROM media m JOIN media_library_groups mg ON mg.id=m.id
        LEFT JOIN playback_state ps ON ps.media_id=m.id AND ps.user_id=$2
        WHERE mg.group_key=$1 ORDER BY COALESCE(m.season_number,1),
        m.episode_number NULLS LAST,m.id""",key,user_id)
    episodes=[]
    for row in rows:
        item=dict(row)
        item["filename"]=Path(item.pop("path")).name
        item["season_number"]=item["season_number"] if item["season_number"] is not None else 1
        item["duration"]=item["duration"].total_seconds()
        item["last_position"]=item["last_position"].total_seconds() if item["last_position"] else 0
        item["updated_at"]=item["updated_at"].isoformat() if item["updated_at"] else None
        episodes.append(item)
    active=sorted((x for x in episodes if x["last_position"]>0),key=lambda x:x["updated_at"] or "",reverse=True)
    next_episode=next((x for x in episodes if not x["watched"]),episodes[0])
    return {"id":min(x["id"] for x in episodes),"group_key":key,"episodes":episodes,
            "season_numbers":sorted({x["season_number"] for x in episodes}),
            "resume_episode_id":active[0]["id"] if active else next_episode["id"]}
