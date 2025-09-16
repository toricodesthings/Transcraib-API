import os, asyncio
from typing import List, Dict
from .task_model import Task, FileStatus
from database.task_database import TaskDatabase

async def process_task(task: Task, model, model_name: str, db: TaskDatabase):
    """Process a transcription task and return results."""
    total_files = len(task.files)
    
    for file in task.files:
        try:
            print(f'🔄 Starting file {file.file_index + 1}/{total_files}: {file.file_name}')
            
            file.start_processing()
            db.add_task(task)  # Save immediately so frontend sees processing status
            
            result = await _transcribe_file_with_progress(file, model, task, db)
            
            print(f"✅ File {file.file_name} completed")
            
        except Exception as e:
            print(f"❌ Error transcribing {file.file_name}: {e}")
            file.fail(str(e))
            db.add_task(task)  # Save failure immediately
            
            
        finally:
            if os.path.exists(file.file_path):
                os.remove(file.file_path)
                
    db.add_task(task)  # Final save after all files processed
    print(f"🗂️ All files for task {task.id} processed")

async def _transcribe_file_with_progress(file, model, task: Task, db: TaskDatabase):
    """Transcribe file with independent result storage"""
    
    try:
        # Progress simulation
        progress_steps = [10, 50, 70]
        
        for progress in progress_steps:
            file.update_progress(progress)
            db.add_task(task)  # Save progress
            await asyncio.sleep(0.5)
        
        # Actual transcription
        result = await _transcribe_file(file.file_path, model)
        
        file.update_progress(95)
        db.add_task(task)  # Save progress
        
        # CHANGED: Complete file with independent result
        file.complete(
            transcription=result.get("text", ""),
            language=result.get("language"),
            duration=result.get("duration")
        )
        
        # CHANGED: Save immediately - result now available to frontend
        db.add_task(task)
        
        print(f"✅ File {file.file_name} result available")
        
    except Exception as e:
        file.fail(str(e))
        db.add_task(task)
        raise


async def _transcribe_file(file_path: str, model) -> Dict:
    """Transcribe a single file using the provided model"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, model.transcribe, file_path)