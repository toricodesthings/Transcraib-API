"""Cloud transcription via OpenRouter's speech-to-text API (official `openrouter` SDK)."""
import os, re, subprocess, tempfile, time
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from openrouter import OpenRouter
from openrouter.errors import OpenRouterError

from endpoints.transcripts import save_transcript
from endpoints.transcribe import (MAX_FILES_PER_BATCH, MAX_FILE_SIZE, HEAD_SIZE,
                                  validate_file_meta, validate_file_content)

load_dotenv()
router = APIRouter(tags=["Cloud"])

MODELS_TTL = 3600
# OpenRouter caps multipart uploads at 25 MB and providers time out after 60 s per request.
# Chunk length is derived from the file's real FLAC bitrate so each piece lands near CHUNK_MB.
CHUNK_MB = float(os.getenv("CLOUD_CHUNK_MB", "20"))
PARALLEL_CHUNKS = int(os.getenv("CLOUD_PARALLEL_CHUNKS", "4"))
# Each chunk also covers the next OVERLAP_SECONDS so words on a cut appear whole in one of them.
OVERLAP_SECONDS = float(os.getenv("CLOUD_OVERLAP_SECONDS", "3"))
_models_cache = {"at": 0.0, "data": []}


def _key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def _default_model() -> Optional[str]:
    return os.getenv("OPENROUTER_DEFAULT_MODEL", "").strip() or None


def _client() -> OpenRouter:
    if not _key():
        raise HTTPException(503, "Cloud mode not configured: add OPENROUTER_API_KEY to .env and restart")
    return OpenRouter(api_key=_key())


def _flac_chunks(content: bytes) -> List[bytes]:
    """Extract the audio track as lossless mono 16 kHz FLAC, cut into ~CHUNK_MB pieces
    that each run OVERLAP_SECONDS into the next. STT models resample to 16 kHz mono anyway,
    so this loses nothing they'd use."""
    def ffmpeg(*args):
        p = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
                           capture_output=True, timeout=1800)
        if p.returncode:
            raise ValueError("ffmpeg could not decode audio: " + p.stderr.decode(errors="replace")[-300:])

    with tempfile.TemporaryDirectory() as d:
        src, full = Path(d) / "in", Path(d) / "full.flac"
        src.write_bytes(content)
        ffmpeg("-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "flac", str(full))
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(full)], capture_output=True, text=True)
        duration, size = float(p.stdout.strip() or 0), full.stat().st_size
        if size <= CHUNK_MB * 2**20 or not duration:
            return [full.read_bytes()]
        chunk_seconds = CHUNK_MB * 2**20 / (size / duration) - OVERLAP_SECONDS
        chunks, start = [], 0.0
        while start < duration:
            out = Path(d) / f"c{len(chunks)}.flac"
            ffmpeg("-ss", str(start), "-t", str(chunk_seconds + OVERLAP_SECONDS), "-i", str(full), "-c:a", "flac", str(out))
            chunks.append(out.read_bytes())
            start += chunk_seconds
        return chunks


def _merge(a: str, b: str, window: int = 25) -> str:
    """Join two overlapping transcripts, dropping the words they share.
    Looks for the longest common word run between a's tail and b's head; edge words may be
    garbled in either chunk, so this doesn't require an exact suffix/prefix match."""
    aw, bw = a.split(), b.split()
    if not aw or not bw:
        return " ".join(aw + bw)
    norm = lambda ws: [re.sub(r"\W", "", w.lower()) for w in ws]
    tail, head = aw[-window:], bw[:window]
    m = SequenceMatcher(None, norm(tail), norm(head), autojunk=False).find_longest_match(0, len(tail), 0, len(head))
    if m.size < 2:  # no confident overlap found: plain join beats deleting real words
        return " ".join(aw + bw)
    return " ".join(aw[:len(aw) - len(tail) + m.a] + bw[m.b:])


@router.get("/status")
def status():
    return {"configured": bool(_key()), "default_model": _default_model()}


@router.get("/models")
def models():
    if time.time() - _models_cache["at"] > MODELS_TTL:
        try:
            with _client() as c:
                page, data = c.models.list(output_modalities="transcription"), []
                while page:  # SDK paginates: list is under .result.data, .next() fetches more
                    data += [{"id": m.id, "name": m.name} for m in page.result.data]
                    page = page.next()
        except OpenRouterError as e:
            raise HTTPException(502, f"OpenRouter error: {e}")
        _models_cache.update(at=time.time(), data=data)
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
                stem = os.path.splitext(f.filename)[0]
                chunks = _flac_chunks(b)
                def stt(i_chunk):
                    i, c = i_chunk
                    return client.stt.create_transcription_multipart(
                        model=model, file={"file_name": f"{stem}_{i}.flac", "content": c}).text
                with ThreadPoolExecutor(PARALLEL_CHUNKS) as pool:  # map keeps chunk order
                    texts = list(pool.map(stt, enumerate(chunks)))
                text = ""
                for t in texts:
                    text = _merge(text, t or "")
                row["transcription"] = text
                row["chunks"] = len(chunks)
                row["saved_as"] = save_transcript(f.filename, text)
            except OpenRouterError as e:
                row["error"] = f"OpenRouter error: {e}"
            except (ValueError, subprocess.TimeoutExpired) as e:
                row["error"] = str(e)
            out.append(row)
    return out


if __name__ == "__main__":  # quick self-check for the overlap merge
    assert _merge("the cell membrane is made of a lipid", "of a lipid bilayer with proteins") == \
        "the cell membrane is made of a lipid bilayer with proteins"
    assert _merge("so the mitochondria produc", "dria produces ATP for the cell") == \
        "so the mitochondria produc dria produces ATP for the cell"  # <2 shared words: keep both
    assert _merge("today we cover entropy and the second", "and the second law of thermo") == \
        "today we cover entropy and the second law of thermo"
    assert _merge("Hello, World. Next", "world next topic") == "Hello, world next topic"  # matched words: later chunk wins
    assert _merge("", "first chunk") == "first chunk"
    print("merge ok")
