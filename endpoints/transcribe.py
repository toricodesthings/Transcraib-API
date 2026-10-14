from fastapi import APIRouter, File, UploadFile, HTTPException
from tempfile import NamedTemporaryFile
from typing import List
import os

import filetype
from task_management.task_manager import add_task

router = APIRouter()

ALLOWED_MIME = {
    "audio/mpeg",          # .mp3
    "audio/wav",           # .wav
    "audio/x-wav",         # .wav (alt)
    "audio/mp4",           # .m4a/.mp4
    "audio/aac",           # .aac
    "audio/ogg",           # .ogg
    "audio/webm",          # .webm
    "audio/ts",            # .ts
    "text/plain",          # .ts (browsers often detect .ts files as text/plain)
    "video/mp4",           # .mp4 (some browsers send video/* for audio containers)
    "video/quicktime",     # .mov
}

# Safe file extensions for audio/video
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.mp4', '.aac', '.ogg', '.webm', '.ts', '.mov'}

# Actual MIME types (as reported by `filetype`) to verify against file content
SAFE_CONTENT_TYPES = {
    'audio/mpeg', 'audio/x-wav', 'audio/mp4', 'audio/aac',
    'audio/ogg', 'video/mp4', 'video/x-m4v', 'video/quicktime', 'video/webm'
}

EXECUTABLE_SIGNATURES = [
    b'\x4d\x5a',          # PE executable (Windows .exe)
    b'\x7f\x45\x4c\x46',  # ELF executable (Linux)
    b'\xfe\xed\xfa',      # Mach-O executable (macOS)
    b'\xcf\xfa\xed\xfe',  # Mach-O executable (macOS)
]

MAX_FILES_PER_BATCH = 5
MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 1GB
CHUNK_SIZE = 1024 * 1024
HEAD_SIZE = 8192


def validate_file_meta(file: UploadFile) -> str:
    """Validate filename, extension and declared MIME. Returns the lowercased extension."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    if any(char in file.filename for char in dangerous_chars):
        raise HTTPException(status_code=400, detail="Filename contains dangerous characters")

    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Supported types: {', '.join(ALLOWED_MIME)}"
        )

    if file.content_type == "text/plain" and file_ext != ".ts":
        raise HTTPException(
            status_code=400,
            detail=f"text/plain MIME type is only allowed for .ts files, but received {file_ext}"
        )
    return file_ext


def validate_file_content(head: bytes, file_ext: str) -> None:
    """Sniff the real type from the first bytes. .ts (MPEG-TS) isn't sniffable, so only reject executables."""
    if any(head.startswith(sig) for sig in EXECUTABLE_SIGNATURES):
        raise HTTPException(status_code=400, detail="Error: executable files are not allowed")
    if file_ext == ".ts":
        return
    actual_mime = filetype.guess_mime(head)
    if actual_mime not in SAFE_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File content doesn't match expected audio/video format. Detected: {actual_mime}"
        )


async def save_upload(file: UploadFile) -> str:
    """Validate and stream an upload to a temp file in chunks, enforcing MAX_FILE_SIZE."""
    file_ext = validate_file_meta(file)
    tmp = NamedTemporaryFile(delete=False, suffix=file_ext)
    size = 0
    try:
        with tmp:
            while chunk := await file.read(CHUNK_SIZE):
                if size == 0:
                    validate_file_content(chunk[:HEAD_SIZE], file_ext)
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail="File too large")
                tmp.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="File is empty")
    except BaseException:
        os.remove(tmp.name)
        raise
    print(f"✅ File validation passed for: {file.filename} ({size} bytes)")
    return tmp.name


@router.post("/transcribe")
async def transcribe_audio(
    files: List[UploadFile] = File(..., description="Audio/video files to transcribe (max 5)")
):
    if len(files) > MAX_FILES_PER_BATCH:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES_PER_BATCH} files allowed")

    temp_file_paths = []
    try:
        for file in files:
            temp_file_paths.append(await save_upload(file))
        task_id = await add_task(temp_file_paths, [f.filename for f in files])
    except Exception as e:
        for path in temp_file_paths:
            if os.path.exists(path):
                os.remove(path)
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Failed to save and process upload. Reason: {e}")

    return {
        "task_id": task_id,
        "status": "queued",
        "message": f"Successfully queued {len(files)} file(s) for transcription",
        "file_count": len(files),
        "files": [f.filename for f in files]
    }
