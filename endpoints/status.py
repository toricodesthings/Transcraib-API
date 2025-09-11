from fastapi import APIRouter, HTTPException
from task_management import task_manager

router = APIRouter()

# Endpoint to get status of transcription tasks
@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get the status of a specific transcription task."""
    # Retrieve task status from task manager
    status = task_manager.get_status(task_id)
    
    # If task not found, raise 404 error
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")

    return status

# Endpoint to get current queue information
@router.get("/queue")
async def get_queue_info():
    """Get information about the current task queue."""
    
    queue_info = task_manager.get_queue_info()
    return queue_info

# Endpoint to get results of completed transcription tasks
@router.get("/results/{task_id}")
async def get_task_results(task_id: str):
    """Get the results of a completed transcription task."""
    
    status = task_manager.get_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="Error: task not found")
    
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Error: task not completed yet. Try again later.")

    # Return only relevant results data
    return {
        "task_id": task_id,
        "status": status["status"],
        "completed_at": status["completed_at"],
        "results": status["results"]
    }