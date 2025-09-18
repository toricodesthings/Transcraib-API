import asyncio
from typing import Optional, List, Dict
from .task_model import Task, TaskFile, FileStatus
from database.task_database import TaskDatabase
from .task_processor import process_task

# Global instances and state
db = TaskDatabase()

# Track the ID of the currently processing task
current_task_id: Optional[str] = None

# Global trackiing of queue state
is_running = False

# Global whisper model configuration
model = None
model_name = None
def set_model(whisper_model, name: str):
    """Set the Whisper model for processing tasks."""
    global model, model_name
    model = whisper_model
    model_name = name
    
# The main function to add a task to the queue
async def add_task(file_paths: List[str], user_id: Optional[str] = None) -> str:
    """Add a new task to the queue and start processing if not already running."""
    global is_running
    
    task = Task(file_paths, user_id)
    db.add_task(task)
    
    # Start queue processing if not already running
    if not is_running:
        asyncio.create_task(_process_queue())
        
    return task.id

def get_task(task_id: str) -> Optional[Task]:
    """Retrieve a task by its ID."""
    return db.retrieve_task(task_id)

def get_file(task_id: str, file_index: int) -> Optional[TaskFile]:
    """Get specific file in a task by task id and file index"""
    task = db.retrieve_task(task_id)
    if task:
        return task.get_file(file_index)
    return None

def get_status(task_id: str) -> Optional[Dict]:
    """Get the status of a specific task with file-level details."""
    task = db.retrieve_task(task_id)
    if task:
        return task.json_response_format()
    return None

def get_completed_results(task_id: str) -> Optional[Dict]:
    task = db.retrieve_task(task_id)
    if not task:
        return None
    
    completed_files = task.get_completed_files()
    return {
        "task_id": task_id,
        "completed_count": len(completed_files),
        "total_count": len(task.files),
        "results": [
            {
                "file_index": f.file_index,
                "file_name": f.file_name,
                "transcription": f.transcription,
                "language": f.language,
                "duration": f.duration,
                "completed_at": f.completed_at.isoformat()
            }
            for f in completed_files
        ]
    }

# Get file-specific result
def get_file_result(task_id: str, file_index: int) -> Optional[Dict]:
    """Get result for a specific file if completed."""
    file = get_file(task_id, file_index)
    if file and file.file_has_result():
        return {
            "task_id": task_id,
            "file_index": file_index,
            "file_name": file.file_name,
            "transcription": file.transcription,
            "language": file.language,
            "duration": file.duration,
            "completed_at": file.completed_at.isoformat()
        }
    return None

def get_queue_info_for_task(task_id: str) -> Dict:
    """Get queue information specific to a task."""
    task = db.retrieve_task(task_id)
    if not task:
        return {"queue_length": 0, "is_processing": False, "current_task": None}
    
    # Check if this task has started processing
    task_has_started = any(file.status != FileStatus.PENDING for file in task.files)
    
    if task_has_started:
        # Task is processing or completed
        return {
            "queue_length": 0,  # Not in queue anymore
            "is_processing": current_task_id == task_id,
            "current_task": get_status(task_id)
        }
    else:
        # Task is still pending - calculate position in queue
        position = db.get_task_queue_position(task_id)
        return {
            "queue_length": position,
            "is_processing": False,
            "current_task": None
        }

def get_queue_info() -> Dict:
    """Get general queue statistics."""
    pending_count = db.count_truly_pending_tasks()  # Only count tasks that haven't started
    
    return {
        "queue_length": pending_count,
        "is_processing": current_task_id is not None,
        "current_task": get_status(current_task_id) if current_task_id else None
    }

# Ensure only one task is in processing at a time, private function
async def _process_queue():
    """Process tasks in the queue one at a time."""
    global is_running, current_task_id
    
    is_running = True
    try:
        while True:
            pending_tasks = db.retrieve_pending()
            # If no pending tasks, exit loop
            if not pending_tasks:
                break
            
            # Get the next task in the queue
            task = pending_tasks[0]
            
            # Mark as current task
            current_task_id = task.id
            
            # Change state to processing
            print(f"🔄 Processing task {task.id} with {len(task.files)}")
            
            # Process the task (calling task processor function)
            try:
                print(f"📋 Starting transcription for task {task.id} with model {model_name}")
                await process_task(task, model, model_name, db)
                
                completed_count = len(task.get_completed_files())
                failed_count = len(task.get_failed_files())
                print(f"✅ Task {task.id} completed: {completed_count} successful, {failed_count} failed")
            
            except Exception as e:
                print(f"❌ Error processing task {task.id}: {e}")

                for file in task.files:
                    if file.status in [FileStatus.PENDING, FileStatus.PROCESSING]:
                        file.fail(f"Task processing error: {str(e)}")
                db.add_task(task)
        
            # Clear current task before moving to next
            current_task_id = None
            await asyncio.sleep(0.5)  # Brief pause between tasks
            
    except Exception as e:
        print(f"Error detected in queue processing: {e}")
        current_task_id = None
    finally: 
        is_running = False
        current_task_id = None
        print("✅ Queue processing completed")