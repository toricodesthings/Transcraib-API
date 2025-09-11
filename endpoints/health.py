from fastapi import APIRouter
from task_management import task_manager
import time

router = APIRouter()

# Function to create health endpoint with dependencies
def create_health_endpoint(hw_info, start_time, api_version):
    """Create health endpoint with injected dependencies."""
    
    # Basic health check
    @router.get("/health")
    def health_alt():
        current_model = task_manager.model_name
        
        return {"status": "normal", 
                "system_gpu": hw_info["gpu_name"], 
                "whispermodel": current_model,
                "uptime_seconds": round(time.time() - start_time, 1),
                "api_version": api_version}
    
    return router