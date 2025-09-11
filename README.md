# Whisper Transcription API

A FastAPI-based audio/video transcription service using OpenAI's Whisper model with queue management and hardware optimization. This API can be ran locally, refer to installation for how to. 

## Features

- 🎵 **Multi-format Audio/Video Support**: MP3, WAV, MP4, M4A, AAC, OGG, WebM, TS, MOV
- 🔄 **Queue Management**: Background task processing with real-time status updates
- 🚀 **Hardware Detection**: Automatic GPU detection and model selection
- 📁 **Batch Processing**: Upload up to 5 files per request

## Quick Start

### Prerequisites

- Python 3.8+
- CUDA-compatible GPU (optional, for faster processing)
- FFmpeg (for audio/video processing)

### Installation

```bash
git clone "add url twin"
cd transcraib-api
pip install -r requirements.txt
```

### Running the API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 9005
```

The API will be available at `http://localhost:9005`

## API Endpoints

### Health Check
```http
GET /health
```
Returns system status, hardware info, current model, and uptime.

**Response:**
```json
{
  "status": "normal",
  "system_gpu": "NVIDIA GeForce RTX 4090",
  "whispermodel": "turbo",
  "uptime_seconds": 123.4,
  "api_version": "1.0.0"
}
```

### Transcribe Audio/Video
```http
POST /transcribe
```
Upload files for transcription.

**Parameters:**
- `files`: Audio/video files (max 5, 1GB each)
- `user_id`: Optional user identifier

**Response:**
```json
{
  "task_id": "somethingsomething123",
  "status": "queued",
  "message": "Successfully queued 2 file(s) for transcription",
  "file_count": 2,
  "files": ["audio1.mp3", "video1.mp4"],
  "next_steps": {
    "view_status": "/task/status/somethingsomething123",
    "view_results": "/task/results/somethingsomething123"
  }
}
```

### Check Task Status
```http
GET /task/status/{task_id}
```
Get real-time status of a transcription task.

**Response:**
```json
{
  "id": "somethingsomething123",
  "status": "processing",
  "progress": 45,
  "user_id": "user123",
  "file_count": 2,
  "created_at": "2024-01-15T10:30:00Z",
  "started_at": "2024-01-15T10:30:05Z"
}
```

### Get Task Results
```http
GET /task/results/{task_id}
```
Retrieve transcription results for completed tasks.

**Response:**
```json
{
  "id": "abc123",
  "status": "completed",
  "results": [
    {
      "file_index": 0,
      "filename": "audio1.mp3",
      "model_used": "turbo",
      "language": "en",
      "text": "Hello, this is a transcription of the audio file."
    }
  ]
}
```

### Queue Information
```http
GET /task/queue
```
Get current queue status and statistics.

**Response:**
```json
{
  "queue_length": 3,
  "is_processing": true,
  "current_task": {
    "id": "def456",
    "status": "processing",
    "progress": 25
  }
}
```

### Change Whisper Model
```http
POST /model/set
```
Force a specific Whisper model for transcription.

**Request Body:**
```json
{
  "model_name": "base"
}
```

**Available Models:**
- `tiny` (1GB VRAM) - Fastest, lowest accuracy
- `base` (1GB VRAM) - Good speed/accuracy balance
- `small` (2GB VRAM) - Better accuracy
- `medium` (5GB VRAM) - High accuracy
- `large` (10GB VRAM) - Highest accuracy
- `turbo` (6GB VRAM) - Fastest large model

**Response:**
```json
{
  "success": true,
  "message": "Model successfully set to 'base'",
  "previous_model": "turbo",
  "new_model": "base",
  "gpu_enabled": true,
  "hardware_info": {
    "gpu_count": 1,
    "total_vram_gb": 24.0,
    "system_ram_gb": 32.0
  }
}
```

## Usage Examples

### Using curl

**Upload for transcription:**
```bash
curl -X POST "http://localhost:8000/transcribe" \
  -F "files=@audio.mp3" \
  -F "user_id=user123"
```

**Check status:**
```bash
curl "http://localhost:8000/task/status/abc123"
```

**Change model:**
```bash
curl -X POST "http://localhost:8000/model/set" \
  -H "Content-Type: application/json" \
  -d '{"model_name": "base"}'
```

## Supported File Formats

### Audio Formats
- **MP3** (audio/mpeg)
- **WAV** (audio/wav, audio/x-wav)
- **M4A/MP4** (audio/mp4)
- **AAC** (audio/aac)
- **OGG** (audio/ogg)
- **WebM** (audio/webm)

### Video Formats
- **MP4** (video/mp4)
- **MOV** (video/quicktime)
- **TS** (audio/ts, video transport streams)

### File Limits
- **Maximum file size**: 1GB per file (Subject to change)
- **Maximum files per batch**: 5 files
- **Supported extensions**: .mp3, .wav, .m4a, .mp4, .aac, .ogg, .webm, .ts, .mov

## Hardware Requirements

### Minimum Requirements
- **CPU**: Any modern x64 processor
- **RAM**: 4GB system memory
- **Storage**: 2GB free space

### Recommended for GPU Acceleration
- **GPU**: NVIDIA GPU with CUDA support
- **VRAM**: 
  - 2GB+ for small models
  - 6GB+ for turbo/medium models
  - 10GB+ for large models

### Model Performance Guide (Based on OpenAI's Documentation)
| Model | VRAM | CPU RAM | Speed | Accuracy |
|-------|------|---------|--------|----------|
| tiny  | 1GB  | 1GB     | Fastest | Lowest |
| base  | 1GB  | 1GB     | Fast   | Good |
| small | 2GB  | 2GB     | Medium | Better |
| medium| 5GB  | 5GB     | Slow   | High |
| large | 10GB | 10GB    | Slowest| Highest |
| turbo | 6GB  | 6GB     | Fast   | High |

## Configuration

The API automatically detects available hardware and selects the optimal model. You can override this selection using the `/model/set` endpoint if you are running this API yourself locally.

## Error Handling

The API returns detailed error messages for common issues:

- **400 Bad Request**: Invalid file format, size, or request parameters
- **404 Not Found**: Task not found
- **413 Payload Too Large**: File exceeds size limits
- **422 Unprocessable Entity**: Invalid request format
- **500 Internal Server Error**: Processing or system errors

## Security Features

- **File Type Validation**: Checks both MIME type and file content
- **Malware Protection**: Scans for executable file signatures
- **Path Traversal Protection**: Validates filenames for dangerous characters
- **Size Limits**: Enforces maximum file sizes
- **Temporary File Cleanup**: Automatically removes uploaded files after processing

## Todo List:

- Dockerize the API
- Implement better error checking and handling
- Integrate with frontend (in progress)
- Better testing interface
- Scaling to handle multiple transcriptions at a time
- Better logging 

## License

This project is licensed under the MIT License - see the LICENSE file for details.