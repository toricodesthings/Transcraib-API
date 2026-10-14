from fastapi import APIRouter
from task_management import task_manager
import time

router = APIRouter()


@router.get("/health")
def health_alt():
    return {"status": "normal",
            "system_gpu": task_manager.hw["gpu_name"],
            "whispermodel": task_manager.model_name,
            "uptime_seconds": round(time.time() - task_manager.start_time, 1),
            "api_version": task_manager.api_version}
