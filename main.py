import os, time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from task_management import task_manager
from hardware_utils import detect_hardware, model_pick
from endpoints.transcribe import router as transcribe_router
from endpoints.set import router as set_model_router
from endpoints.status import router as status_router
from endpoints.cloud import router as cloud_router
from endpoints.transcripts import router as transcripts_router

API_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Detecting hardware...")
    hw = detect_hardware()
    print("Hardware Info:", hw)
    if hw["gpu_count"] == 0:
        print("Warning: No GPU detected, transcription will use CPU, this may be slow.")

    name, gpu = model_pick(hw)
    print("Selected Model:", name)
    task_manager.hw = hw
    task_manager.gpu = gpu
    task_manager.start_time = time.time()
    task_manager.api_version = API_VERSION
    task_manager.set_model(None, name)  # downloaded/loaded on the first local transcription

    print("Cleared existing tasks from previous sessions:", task_manager.clear_all())
    print("Transcription API Ready")
    yield


app = FastAPI(
    title="Whisper Transcription API",
    version=API_VERSION,
    description="Audio/Video transcription API with queue management",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.include_router(set_model_router, prefix="/model")
app.include_router(transcribe_router)
app.include_router(status_router, prefix="/task", tags=["Task Management"])
app.include_router(cloud_router, prefix="/cloud")
app.include_router(transcripts_router, prefix="/transcripts")


@app.get("/")
def interface():
    return FileResponse(os.path.join(os.path.dirname(__file__), "interface.html"))


@app.get("/health")
def health():
    return {"status": "normal",
            "system_gpu": task_manager.hw["gpu_name"],
            "whispermodel": task_manager.model_name,
            "model_loaded": task_manager.model is not None,
            "uptime_seconds": round(time.time() - task_manager.start_time, 1),
            "api_version": task_manager.api_version}


@app.delete("/admin/clear-all")
def clear_all():
    """Delete all tasks/files. Refused while a task is being transcribed."""
    if task_manager.current_task_id is not None:
        raise HTTPException(status_code=409, detail="A task is currently processing; try again when it finishes")
    return {"success": True, "deleted_counts": task_manager.clear_all()}
