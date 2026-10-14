"""Cloud transcription via OpenRouter's speech-to-text API (official `openrouter` SDK)."""
import os, subprocess, time
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from openrouter import OpenRouter
from openrouter.errors import OpenRouterError

from endpoints.transcribe import (MAX_FILES_PER_BATCH, MAX_FILE_SIZE, HEAD_SIZE,
                                  validate_file_meta, validate_file_content)

load_dotenv()
router = APIRouter(tags=["Cloud"])

# Containers passed through as-is; everything else (mp4/mov/ts/webm/m4a/aac/ogg) is
# re-encoded to mp3 since STT format support varies by provider.
PASSTHROUGH = {".mp3", ".wav"}
MODELS_TTL = 3600
_models_cache = {"at": 0.0, "data": []}


def _key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def _default_model() -> Optional[str]:
    return os.getenv("OPENROUTER_DEFAULT_MODEL", "").strip() or None


def _client() -> OpenRouter:
    if not _key():
        raise HTTPException(503, "Cloud mode not configured: add OPENROUTER_API_KEY to .env and restart")
    return OpenRouter(api_key=_key())


def _to_mp3(content: bytes) -> bytes:
    """Extract/convert the audio track to mono 16 kHz mp3 via ffmpeg (stdin -> stdout)."""
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-vn",
         "-ac", "1", "-ar", "16000", "-b:a", "64k", "-f", "mp3", "pipe:1"],
        input=content, capture_output=True, timeout=600)
    if p.returncode or not p.stdout:
        raise ValueError("ffmpeg could not decode audio: " + p.stderr.decode(errors="replace")[-300:])
    return p.stdout


@router.get("/status")
def status():
    return {"configured": bool(_key()), "default_model": _default_model()}


@router.get("/models")
def models():
    if time.time() - _models_cache["at"] > MODELS_TTL:
        try:
            with _client() as c:
                res = c.models.list(output_modalities="transcription")
        except OpenRouterError as e:
            raise HTTPException(502, f"OpenRouter error: {e}")
        _models_cache.update(at=time.time(), data=[{"id": m.id, "name": m.name} for m in res.data])
    return {"models": _models_cache["data"], "default_model": _default_model()}


@router.post("/transcribe")
def transcribe(files: List[UploadFile] = File(...), model: Optional[str] = Form(None)):
    model = (model or "").strip() or _default_model()
    if not model:
        raise HTTPException(400, "No model given and OPENROUTER_DEFAULT_MODEL is not set")
    if len(files) > MAX_FILES_PER_BATCH:
        raise HTTPException(400, f"Max {MAX_FILES_PER_BATCH} files per batch")
    with _client() as client:
        blobs = [f.file.read() for f in files]
        for f, b in zip(files, blobs):  # fail the whole batch before spending credits
            validate_file_content(b[:HEAD_SIZE], validate_file_meta(f))
            if not b:
                raise HTTPException(400, f"{f.filename} is empty")
            if len(b) > MAX_FILE_SIZE:
                raise HTTPException(413, f"{f.filename} is too large")
        out = []
        for f, b in zip(files, blobs):
            row = {"file_name": f.filename, "transcription": None, "model": model, "error": None}
            try:
                name = f.filename
                if os.path.splitext(name.lower())[1] not in PASSTHROUGH:
                    b, name = _to_mp3(b), os.path.splitext(name)[0] + ".mp3"
                res = client.stt.create_transcription_multipart(
                    model=model, file={"file_name": name, "content": b})
                row["transcription"] = res.text
            except OpenRouterError as e:
                row["error"] = f"OpenRouter error: {e}"
            except (ValueError, subprocess.TimeoutExpired) as e:
                row["error"] = str(e)
            out.append(row)
    return out
