import asyncio
from typing import Optional, List, Dict
from .task_model import Task
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

async def add_task(file_paths: List[str], user_id: Optional[str] = None) -> str:
    """Add a new task to the queue and start processing if not already running."""
    global is_running
    
    task = Task(file_paths, user_id)
    db.add_task(task)
    
    # Start queue processing if not already running
    if not is_running:
        asyncio.create_task(_process_queue())
        
    return task.id

def get_status(task_id: str) -> Optional[Dict]:
    """Get the status of a specific task."""
    task = db.retrieve_task(task_id)
    if task:
        return task.response_format()
    return None

def get_queue_info() -> Dict:
    """Get queue statistics and current processing state."""
    pending_count = db.count_pending()
    current_task = None
    
    if current_task_id:
        current_task = get_status(current_task_id)
    
    return {
        "queue_length": pending_count,
        "is_processing": current_task_id is not None,
        "current_task": current_task
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
            print(f"🔄 Processing task {task.id}...")
            task.start_processing()
            db.add_task(task)
            
            # Process the task (calling task processor function)
            try:
                print(f"📋 Starting transcription for task {task.id} with model {model_name}")
                await process_task(task, model, model_name, db)
                print(f"✅ Successfully completed task {task.id}")
            except Exception as e:
                print(f"❌ Error processing task {task.id}: {e}")
                task.fail(str(e))
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