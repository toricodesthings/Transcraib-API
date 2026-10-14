from fastapi import APIRouter, HTTPException
from task_management import task_manager

router = APIRouter()


@router.delete("/clear-all")
async def clear_all():
    """Delete all tasks/files. Refused while a task is being transcribed."""
    if task_manager.current_task_id is not None:
        raise HTTPException(status_code=409, detail="A task is currently processing; try again when it finishes")
    return {"success": True, "deleted_counts": task_manager.clear_all()}
