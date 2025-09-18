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
            
            await _transcribe_file_with_progress(file, model, task, db)
            
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
        from mutagen import File
        # Get file duration for progress estimation
        audio_file = File(file.file_path)
        duration = 0
        if audio_file and audio_file.info:
            duration = audio_file.info.length
        
        # Estimate transcription time (6x faster than file duration)
        estimated_time = duration / 6 if duration > 0 else 30  # fallback to 30 seconds
        progress_interval = estimated_time / 4  # 94intervals for 10-90% progress
        
        # Start transcription task
        transcription_task = asyncio.create_task(_transcribe_file(file.file_path, model))
        
        # Update progress while transcription runs
        progress = 10
        while not transcription_task.done() and progress < 95:
            file.update_progress(progress)
            db.add_task(task)  # Save progress
            await asyncio.sleep(progress_interval)
            progress += 20
        
        # Wait for transcription to complete
        result = await transcription_task
        
        # Complete file and save result when done
        file.complete(
            transcription=result.get("text", ""),
            language=result.get("language"),
            duration=result.get("duration")
        )
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