import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from hardware_utils import model_override, load_model
from task_management import task_manager

router = APIRouter()


class ModelRequest(BaseModel):
    model_name: str


@router.post("/set")
async def force_model(request: ModelRequest):
    """Force a specific model for transcription."""
    hw, gpu = task_manager.hw, task_manager.gpu
    try:
        validated_model = model_override(request.model_name, hw, gpu)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # The queue holds this lock for the whole transcription, so we never swap mid-file.
    if task_manager.model_lock.locked():
        raise HTTPException(status_code=409, detail="Transcription in progress; try again when the queue is idle")

    async with task_manager.model_lock:
        previous_model = task_manager.model_name
        # Drop the old model first so both never sit in VRAM together.
        task_manager.set_model(None, None)
        loop = asyncio.get_running_loop()
        try:
            new_model, task_manager.gpu = await loop.run_in_executor(None, load_model, validated_model, hw, gpu)
            task_manager.set_model(new_model, validated_model)
        except Exception as e:
            old, _ = await loop.run_in_executor(None, load_model, previous_model, hw, gpu)
            task_manager.set_model(old, previous_model)
            raise HTTPException(status_code=500, detail=f"Failed to set model: {e}")

    return {
        "success": True,
        "message": f"Model successfully set to '{validated_model}'",
        "previous_model": previous_model,
        "new_model": validated_model,
        "gpu_enabled": task_manager.gpu,
        "hardware_info": {
            "gpu_count": hw["gpu_count"],
            "total_vram_gb": hw["total_vram_bytes"] / (1024**3) if hw["total_vram_bytes"] else None,
            "system_ram_gb": hw["system_ram_bytes"] / (1024**3)
        }
    }
