from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from tempfile import NamedTemporaryFile
import os

import magic
from typing import List, Optional
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

# Actual MIME types to verify against file content
SAFE_CONTENT_TYPES = {
    'audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/aac', 
    'audio/ogg', 'audio/ts', 'video/mp4', 'video/quicktime'
}

MAX_FILES_PER_BATCH = 5
MAX_FILE_SIZE = 1 * 1024 * 1024 * 1024  # 1GB

def validate_file_safety(file: UploadFile, content: bytes) -> None:
    """
    Validate file safety before processing.
    
    Args:
        file: The uploaded file object
        content: The file content as bytes
        
    Raises:
        HTTPException: If file is unsafe or invalid
    """
    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    
    # Check if content is empty
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Validate filename and extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Check for dangerous characters in filename
    dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    if any(char in file.filename for char in dangerous_chars):
        raise HTTPException(status_code=400, detail="Filename contains dangerous characters")
    
    # Check file extension
    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file extension: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check declared MIME type with special handling for .ts files
    file_ext = os.path.splitext(file.filename.lower())[1]
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {file.content_type}. Supported types: {', '.join(ALLOWED_MIME)}"
        )
    
    # Special validation: only allow text/plain for .ts files
    if file.content_type == "text/plain" and file_ext != ".ts":
        raise HTTPException(
            status_code=400, 
            detail=f"text/plain MIME type is only allowed for .ts files, but received {file_ext}"
        )
    
    # Verify actual file content using python-magic (optional but recommended)
    try:
        actual_mime = magic.from_buffer(content, mime=True)
        # Special handling for .ts files - they can be detected as various MIME types
        if file_ext == ".ts":
            # Allow .ts files to have various MIME types since they can be transport streams
            # or sometimes misdetected as other types
            pass  # Skip content validation for .ts files
        elif actual_mime not in SAFE_CONTENT_TYPES:
            raise HTTPException(
                status_code=400, 
                detail=f"File content doesn't match expected audio/video format. Detected: {actual_mime}"
            )
    except Exception:
        # If magic fails, continue with basic validation
        # This ensures the API still works even if python-magic isn't available
        pass
    
    # Check for executable signatures (basic malware protection)
    executable_signatures = [
        b'\x4d\x5a',  # PE executable (Windows .exe)
        b'\x7f\x45\x4c\x46',  # ELF executable (Linux)
        b'\xfe\xed\xfa',  # Mach-O executable (macOS)
        b'\xcf\xfa\xed\xfe',  # Mach-O executable (macOS)
    ]
    
    for signature in executable_signatures:
        if content.startswith(signature):
            raise HTTPException(status_code=400, detail="Error: executable files are not allowed")
    
    print(f"✅ File validation passed for: {file.filename} ({len(content)} bytes)")

def create_transcribe_endpoint(model, model_name):
    """Create transcribe endpoint with injected model dependency."""
    
    # Note: Model is already set in main.py, no need to set it again here
    
    # Endpoint to upload files for transcription
    @router.post("/transcribe")
    async def transcribe_audio(
        files: List[UploadFile] = File(..., description="Audio/video files to transcribe (max 5)"),
        user_id: Optional[str] = Form(None, description="Optional user identifier")
    ):
        
        # Validate number of files uploaded, reject if too many
        if len(files) > MAX_FILES_PER_BATCH:
            raise HTTPException(status_code=400, detail=f"Maximum {MAX_FILES_PER_BATCH} files allowed")
        
        # List to track temp file paths
        temp_file_paths = []
    
        # Process each uploaded file    
        try:
            for file in files:
                # Read file content
                content = await file.read()
                
                # Validate file safety before processing
                validate_file_safety(file, content)
                
                # Write to temp file and add to list
                temp_file = NamedTemporaryFile(delete=False, suffix=f"_{file.filename}")
                temp_file.write(content)
                temp_file.close()
                temp_file_paths.append(temp_file.name)
            
            # Create a new transcription task
            task_id = await add_task(temp_file_paths, user_id)
            
            # Immediate return response with task details and next steps
            return {
                "task_id": task_id,
                "status": "queued",
                "message": f"Successfully queued {len(files)} file(s) for transcription",
                "file_count": len(files),
                "files": [f.filename for f in files]
            }
        
        # Cleanup temp files on error
        except HTTPException:
            # Clean up temp files on validation error
            for path in temp_file_paths:
                if os.path.exists(path):
                    os.remove(path)
            raise        
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save and process upload. Reason: {e}")
    
    return router