import whisper
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from hardware_utils import model_override
from task_management import task_manager

router = APIRouter()

class ModelRequest(BaseModel):
    model_name: str

def create_model_endpoint(hw_info, current_model_name, gpu):
    """Create model override endpoint with injected dependencies."""
    
    @router.post("/set")
    def force_model(request: ModelRequest):
        """Force a specific Whisper model for transcription."""
        try:
            # Validate the model using model_override with GPU defaulted to True
            validated_model = model_override(request.model_name, hw_info, gpu)
            
            # Load the new model
            print(f"Loading model: {validated_model}")
            new_model = whisper.load_model(validated_model, device="cuda" if gpu else "cpu")
            
            # Set the model globally in task_manager
            task_manager.set_model(new_model, validated_model)
            
            return {
                "success": True,
                "message": f"Model successfully set to '{validated_model}'",
                "previous_model": current_model_name,
                "new_model": validated_model,
                "gpu_enabled": gpu,
                "hardware_info": {
                    "gpu_count": hw_info["gpu_count"],
                    "total_vram_gb": hw_info["total_vram_bytes"] / (1024**3) if hw_info["total_vram_bytes"] else None,
                    "system_ram_gb": hw_info["system_ram_bytes"] / (1024**3)
                }
            }
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to set model: {str(e)}")
    
    return router