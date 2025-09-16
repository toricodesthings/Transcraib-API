from fastapi import APIRouter, HTTPException
from task_management import task_manager

router = APIRouter()

# Endpoint to get status of transcription tasks
@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """Get task status with independent file results"""
    task = task_manager.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail={
            "error": "TASK_NOT_FOUND",
            "message": f"Task {task_id} not found"
        })

    return task.json_response_format()

# Get status of individual file within a task
@router.get("/status/{task_id}/file/{file_index}")
async def get_file_status(task_id: str, file_index: int):
    """Get status and progress of a specific file within a task"""
    
    file = task_manager.get_file(task_id, file_index)
    if not file:
        raise HTTPException(status_code=404, detail={
            "error": "FILE_NOT_FOUND",
            "message": f"File {file_index} not found in task {task_id}"
        })
    
    return {
        "task_id": task_id,
        "file": file.json_response_format()
    }

# Get only completed results
@router.get("/results/{task_id}/completed")
async def get_completed_results(task_id: str):
    """Get only the completed file results (available immediately)"""
    
    completed_results = task_manager.get_completed_results(task_id)
    if completed_results is None:
        raise HTTPException(status_code=404, detail={
            "error": "TASK_NOT_FOUND",
            "message": f"Task {task_id} not found"
        })
    
    return completed_results

# Get result of individual file within a task
@router.get("/results/{task_id}/file/{file_index}")
async def get_file_result(task_id: str, file_index: int):
    """Get result for individual file"""
    
    result = task_manager.get_file_result(task_id, file_index)
    if not result:
        file = task_manager.get_file(task_id, file_index)
        if not file:
            raise HTTPException(status_code=404, detail={
                "error": "FILE_NOT_FOUND",
                "message": f"File {file_index} not found in task {task_id}"
            })
        else:
            raise HTTPException(status_code=400, detail={
                "error": "RESULT_NOT_READY",
                "message": f"File {file.file_name} is not completed yet",
                "current_status": file.status.value,
                "current_progress": file.progress
            })
    
    return result


# Task results endpoint
@router.get("/results/{task_id}")
async def get_task_results(task_id: str):
    """Get results for completed task (all files must be done)"""
    
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail={
            "error": "TASK_NOT_FOUND",
            "message": f"Task {task_id} not found"
        })
    
    # Check if any files are still processing
    incomplete_files = [f for f in task.files if f.status.value in ["pending", "processing"]]
    if incomplete_files:
        raise HTTPException(status_code=400, detail={
            "error": "TASK_NOT_COMPLETE",
            "message": f"Task has {len(incomplete_files)} files still processing",
            "incomplete_files": [f.file_name for f in incomplete_files]
        })
    
    return {
        "task_id": task_id,
        "completed_at": max(f.completed_at for f in task.files if f.completed_at).isoformat(),
        "summary": task.json_response_format()["summary"],
        "results": [
            {
                "file_index": f.file_index,
                "file_name": f.file_name,
                "status": f.status.value,
                "transcription": f.transcription,
                "language": f.language,
                "duration": f.duration,
                "error": f.error_message
            }
            for f in task.files
        ]
    }

# Endpoint to get current queue information
@router.get("/queue")
async def get_queue_info():
    """Get information about the current task queue."""
    return task_manager.get_queue_info()

