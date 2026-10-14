import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from task_management import task_manager
from hardware_utils import detect_hardware, model_pick, load_model
from endpoints.health import router as health_router
from endpoints.transcribe import router as transcribe_router
from endpoints.set import router as set_model_router
from endpoints.root import router as root_router
from endpoints.status import router as status_router
from endpoints.admin import router as admin_router
from endpoints.cloud import router as cloud_router

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
    model, gpu = load_model(name, hw, gpu)
    task_manager.hw = hw
    task_manager.gpu = gpu
    task_manager.start_time = time.time()
    task_manager.api_version = API_VERSION
    task_manager.set_model(model, name)

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

app.include_router(health_router)
app.include_router(root_router)
app.include_router(set_model_router, prefix="/model")
app.include_router(transcribe_router)
app.include_router(status_router, prefix="/task", tags=["Task Management"])
app.include_router(admin_router, prefix="/admin")
app.include_router(cloud_router, prefix="/cloud")
