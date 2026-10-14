"""Every finished transcript (local or cloud) is saved as .txt in TRANSCRIPTS_DIR."""
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

TRANSCRIPTS_DIR = Path(os.getenv("TRANSCRIPTS_DIR", "transcripts")).resolve()
router = APIRouter(tags=["Transcripts"])


def save_transcript(source_name: str, text: str) -> str:
    """Write text to <stem>_<timestamp>.txt and return the saved file name."""
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{Path(source_name).stem}_{datetime.now():%Y%m%d-%H%M%S-%f}.txt"
    (TRANSCRIPTS_DIR / name).write_text(text or "", encoding="utf-8")
    return name


@router.get("")
def list_transcripts():
    files = sorted(TRANSCRIPTS_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True) \
        if TRANSCRIPTS_DIR.exists() else []
    return [{"name": p.name, "size": p.stat().st_size,
             "saved_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat()} for p in files]


@router.get("/{name}")
def download_transcript(name: str):
    path = (TRANSCRIPTS_DIR / name).resolve()
    if path.parent != TRANSCRIPTS_DIR or path.suffix != ".txt" or not path.is_file():
        raise HTTPException(404, "Transcript not found")
    return FileResponse(path, media_type="text/plain", filename=name)
