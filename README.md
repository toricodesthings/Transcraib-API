# 🎵 TranscrAIb - Whisper Transcription API

A FastAPI-based audio/video transcription service using OpenAI's Whisper model with advanced queue management, file-level progress tracking, and hardware optimization. This API can be run locally with real-time progress monitoring for each individual file.

## ✨ Features

- 🎵 **Multi-format Audio/Video Support**: MP3, WAV, MP4, M4A, AAC, OGG, WebM, TS, MOV
- 🔄 **Advanced Queue Management**: Background task processing with real-time status updates
- � **File-Level Progress Tracking**: Monitor progress of each file independently
- ⚡ **Immediate Results**: Get transcription results as soon as each file completes
- �🚀 **Hardware Detection**: Automatic GPU detection and optimal model selection
- 📁 **Batch Processing**: Upload up to 5 files per request with independent processing
- 🛡️ **Security Features**: Comprehensive file validation and malware protection
- 🧹 **Admin Controls**: System management with clear all functionality

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
Upload files for transcription. Returns a task ID for tracking progress.

**Parameters:**
- `files`: Audio/video files (max 5, 1GB each)
- `user_id`: Optional user identifier

**Response (201 Created):**
```json
{
  "task_id": "abc123-def456-789",
  "status": "queued",
  "message": "Successfully queued 3 file(s) for transcription",
  "file_count": 5,
  "files": [
      {
        "filename": "audio1.mp3",
        "size": "5.1 MB",
        "content_type": "audio/mpeg"
      },
      {
        "filename": "video1.mp4", 
        "size": "10.1 MB",
        "content_type": "video/mp4"
      }
    ]
}
```

### Check Task Status (File-Level Tracking)
```http
GET /task/status/{task_id}
```
Get real-time status with individual file progress and immediate results.

**Response:**
```json
{
  "task_id": "abc123-def456-789",
  "created_at": "2025-01-15T10:30:00",
  "summary": {
    "overall_status": "processing",
    "overall_progress": 65,
    "total_files": 3,
    "completed": 1,
    "failed": 0,
    "processing": 1,
    "pending": 1
  },
  "files": [
    {
      "file_index": 0,
      "filename": "audio1.mp3",
      "status": "completed",
      "progress": 100,
      "result": {
        "transcription": "Hello world, this is a test recording...",
        "language": "en",
        "duration": 45.2
      },
      "error": null,
      "timing": {
        "created_at": "2025-01-15T10:30:00",
        "started_at": "2025-01-15T10:30:05",
        "completed_at": "2025-01-15T10:32:15"
      }
    },
    {
      "file_index": 1,
      "filename": "video1.mp4",
      "status": "processing",
      "progress": 75,
      "result": null,
      "error": null,
      "timing": {
        "created_at": "2025-01-15T10:30:00",
        "started_at": "2025-01-15T10:32:20",
        "completed_at": null
      }
    },
    {
      "file_index": 2,
      "filename": "audio2.wav",
      "status": "pending",
      "progress": 0,
      "result": null,
      "error": null,
      "timing": {
        "created_at": "2025-01-15T10:30:00",
        "started_at": null,
        "completed_at": null
      }
    }
  ],
  "completed_results": [
    {
      "file_index": 0,
      "filename": "audio1.mp3",
      "transcription": "Hello world, this is a test recording...",
      "language": "en",
      "duration": 45.2,
      "completed_at": "2025-01-15T10:32:15"
    }
  ]
}
```

### Get Individual File Status
```http
GET /task/status/{task_id}/file/{file_index}
```
Get status and progress of a specific file within a task.

**Response:**
```json
{
  "task_id": "abc123-def456-789",
  "file": {
    "file_index": 1,
    "filename": "video1.mp4",
    "status": "processing",
    "progress": 75,
    "result": null,
    "error": null,
    "timing": {
      "created_at": "2025-01-15T10:30:00",
      "started_at": "2025-01-15T10:32:20",
      "completed_at": null
    }
  }
}
```

### Get Completed Results Only
```http
GET /task/results/{task_id}/completed
```
Get only the completed file results (available immediately, don't wait for entire batch).

**Response:**
```json
{
  "task_id": "abc123-def456-789",
  "completed_count": 2,
  "total_count": 3,
  "results": [
    {
      "file_index": 0,
      "filename": "audio1.mp3",
      "transcription": "Hello world, this is a test recording...",
      "language": "en",
      "duration": 45.2,
      "completed_at": "2025-01-15T10:32:15"
    },
    {
      "file_index": 2,
      "filename": "audio2.wav",
      "transcription": "This is another audio transcription...",
      "language": "en",
      "duration": 32.1,
      "completed_at": "2025-01-15T10:35:42"
    }
  ]
}
```

### Get Individual File Result
```http
GET /task/results/{task_id}/file/{file_index}
```
Get result for individual file (available immediately when file completes).

**Response:**
```json
{
  "task_id": "abc123-def456-789",
  "file":
  {
    "file_index": 0,
    "filename": "audio1.mp3",
    "transcription": "Hello world, this is a test recording...",
    "language": "en",
    "duration": 45.2,
    "completed_at": "2025-01-15T10:32:15"
  }
}
```

### Get Complete Task Results
```http
GET /task/results/{task_id}
```
Retrieve all transcription results for completed tasks (all files must be done).

**Response:**
```json
{
  "task_id": "abc123-def456-789",
  "completed_at": "2025-01-15T10:35:42",
  "summary": {
    "overall_status": "completed",
    "overall_progress": 100,
    "total_files": 3,
    "completed": 2,
    "failed": 1,
    "processing": 0,
    "pending": 0
  },
  "results": [
    {
      "file_index": 0,
      "filename": "audio1.mp3",
      "status": "completed",
      "transcription": "Hello world, this is a test recording...",
      "language": "en",
      "duration": 45.2,
      "error": null
    },
    {
      "file_index": 1,
      "filename": "video1.mp4",
      "status": "failed",
      "transcription": null,
      "language": null,
      "duration": null,
      "error": "Unsupported video codec"
    },
    {
      "file_index": 2,
      "filename": "audio2.wav",
      "status": "completed",
      "transcription": "This is another audio transcription...",
      "language": "en",
      "duration": 32.1,
      "error": null
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
  "queue_length": 2,
  "is_processing": true,
  "current_task_id": "def456-789-abc",
  "current_task_summary": {
    "overall_status": "processing",
    "overall_progress": 45,
    "total_files": 3,
    "completed": 1,
    "processing": 1,
    "pending": 1
  },
  "pending_tasks": [
    {
      "task_id": "ghi789-abc-123",
      "file_count": 2,
      "created_at": "2025-01-15T10:45:00"
    }
  ]
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
curl -X POST "http://localhost:9005/transcribe" \
  -F "files=@audio.mp3" \
  -F "files=@video.mp4" \
  -F "user_id=user123"
```

**Check status with file-level details:**
```bash
curl "http://localhost:9005/task/status/abc123-def456-789"
```

**Get completed results only:**
```bash
curl "http://localhost:9005/task/results/abc123-def456-789/completed"
```

**Get individual file result:**
```bash
curl "http://localhost:9005/task/results/abc123-def456-789/file/0"
```

**Change model:**
```bash
curl -X POST "http://localhost:9005/model/set" \
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
- **Maximum file size**: 1GB per file
- **Maximum files per batch**: 5 files
- **Supported extensions**: .mp3, .wav, .m4a, .mp4, .aac, .ogg, .webm, .ts, .mov

## Hardware Requirements

### Minimum Requirements
- **CPU**: Any modern x64 processor
- **RAM**: 8GB system memory
- **Storage**: 5GB free space for models

### Recommended for GPU Acceleration
- **GPU**: NVIDIA GPU with CUDA support (AMD SUPPORT SOON)
- **VRAM**: 
  - 2GB+ for small models
  - 6GB+ for turbo/medium models
  - 10GB+ for large models

### Model Performance Guide
| Model | VRAM | CPU RAM | Speed | Accuracy |
|-------|------|---------|--------|----------|
| tiny  | 1GB  | 1GB     | Fastest | Lowest |
| base  | 1GB  | 1GB     | Fast   | Good |
| small | 2GB  | 2GB     | Medium | Better |
| medium| 5GB  | 5GB     | Slow   | High |
| large | 10GB | 10GB    | Slowest| Highest |
| turbo | 6GB  | 6GB     | Fast   | High |

## Configuration

The API automatically detects available hardware and selects the optimal model. You can override this selection using the `/model/set` endpoint, this is an admin command, so auth support will be built in.

## Error Handling

The API returns detailed error messages for common issues:
- **400 Bad Request**: Invalid file format, size, or request parameters
- **404 Not Found**: Task not found
- **413 Payload Too Large**: File exceeds size limits
- **415 Unsupported Media Type**: Invalid file format
- **422 Unprocessable Entity**: Invalid request format
- **500 Internal Server Error**: Processing or system errors

### Error Response Format
```json
{
  "error": "FILE_TOO_LARGE",
  "message": "File 'audio.mp3' is too large. Size: 1.2 GB, Maximum allowed: 1.0 GB",
  "file": "audio.mp3",
  "file_index": 0
}
```

## Security Features

- **File Type Validation**: Checks both MIME type and file content
- **Malware Protection**: Scans for executable file signatures
- **Path Traversal Protection**: Validates filenames for dangerous characters
- **Size Limits**: Enforces maximum file sizes
- **Temporary File Cleanup**: Automatically removes uploaded files after processing

## Test Interface

The API includes a built-in test interface accessible at `http://localhost:9005/test_interface.html` featuring:

- **File Upload**: Drag & drop or select multiple files
- **Real-time Progress**: Individual file progress bars and status
- **Immediate Results**: View transcriptions as files complete
- **Debug Console**: Real-time logging and system status

## Architecture Overview

### File-Centric Design
- Each file within a task has independent status and progress tracking
- Results available immediately when individual files complete
- No need to wait for entire batch to finish

### Database Structure
- **Tasks Table**: Container with task ID and metadata
- **Task Files Table**: Individual file records with status, progress, and results
- **Real-time Updates**: Database updates on every progress change

### Processing Flow
1. **Upload** → Files validated and task created
2. **Queue** → Task added to processing queue
3. **Process** → Files processed individually with progress updates
4. **Results** → Each file result available immediately upon completion

## Todo List:

- [ ] Dockerize the API for easy deployment
- [ ] Add authentication and user management
- [ ] Implement file result saving
- [ ] Add support for custom Whisper model fine-tuning
- [ ] Implement batch download of multiple results
- [ ] Add support for subtitle file generation (SRT, VTT)
- [ ] Create comprehensive API rate limiting
- [ ] Add detailed logging and monitoring dashboard
- [ ] Add support for speaker diarization

## License

This project is licensed under the MIT License - see the LICENSE file for details.