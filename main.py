from fastapi import FastAPI
import whisper, time
from database.task_database import TaskDatabase
from task_management import task_manager
from hardware_utils import detect_hardware, model_pick
from endpoints.health import create_health_endpoint
from endpoints.transcribe import create_transcribe_endpoint
from endpoints.setmodel import create_model_endpoint
from endpoints.root import router as root_router

from endpoints.status import router as status_router

# API Configuration 
API_VERSION = "1.0.0"
app = FastAPI(
    title="Whisper Transcription API", 
    version=API_VERSION,
    description="Audio/Video transcription API with queue management"
)

def main():
    db = TaskDatabase()
    
    # Log & Hardware Detection
    print("Detecting hardware...")
    HW = detect_hardware()
    print("Hardware Info:", HW)
    
    if HW["gpu_count"] == 0:
        print("Warning: No GPU detected, Transcription will utilize CPU, this may be slow.")
        
    # Load Whisper Model based on hardware
    MODEL_NAME, GPU = model_pick(HW)
    print("Selected Model:", MODEL_NAME)
    model = whisper.load_model(MODEL_NAME, device="cuda" if GPU else "cpu")
    
    # Default a model globally in task_manager (based on initial hardware detection)
    task_manager.set_model(model, MODEL_NAME)

    # Clear any existing tasks from previous sessions
    db.clear_all()
    print("Cleared existing tasks from previous sessions.")
    
    START_TIME = time.time()

    # Initialize the endpoints with dependencies
    health_router = create_health_endpoint(HW, START_TIME, API_VERSION)
    transcribe_router = create_transcribe_endpoint(model, MODEL_NAME)
    set_model_router = create_model_endpoint(HW, MODEL_NAME, GPU)

    # Include the routers and endpoints
    app.include_router(health_router)
    app.include_router(root_router)
    app.include_router(set_model_router, prefix="/model")
    app.include_router(transcribe_router)
    app.include_router(status_router, prefix="/task", tags=["Task Management"])

    
    print("Whisper Transcription API Ready")
    return app
    
app = main()

