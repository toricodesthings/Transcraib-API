import os, asyncio
from typing import List, Dict
from .task_model import Task
from database.task_database import TaskDatabase

async def process_task(task: Task, model, model_name: str, db: TaskDatabase):
    """Process a transcription task and return results."""
    results = []
    total_files = len(task.file_paths)
    
    for i, file_path in enumerate(task.file_paths):
        try:
            # Update progress and save to database
            task.in_progress(int((i+1 / total_files) * 80))
            db.add_task(task)  # Save progress update
            
            print(f'Transcribing file {i+1}/{total_files}: {os.path.basename(file_path)}')
            result = await _transcribe_file(file_path, model)
            
            results.append({
                "file_index": i,
                "filename": os.path.basename(file_path),
                "model_used": model_name,
                "language": result.get("language"),
                "text": result.get("text")
            })
            
        except Exception as e:
            print(f"Error transcribing {file_path}: {e}")
            results.append({
                "file_index": i,
                "filename": os.path.basename(file_path),
                "error": str(e)
            })
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    # Set and save final state
    task.complete(results)
    db.add_task(task)  
    print(f"✅ Task {task.id} completed with {len(results)} results")
    return results

async def _transcribe_file(file_path: str, model) -> Dict:
    """Transcribe a single file using the provided model"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, model.transcribe, file_path)