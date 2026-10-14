import asyncio, os
from typing import Optional, List, Dict
from .task_model import Task, TaskFile, FileStatus
from database import task_database as db
from hardware_utils import load_model
from endpoints.transcripts import save_transcript

current_task_id: Optional[str] = None
is_running = False

# Hardware / runtime info, filled in by main.lifespan
hw: Dict = {}
gpu = False
start_time = 0.0
api_version = ""

# model_lock is held while a task transcribes and while swapping models.
model = None
model_name = None
model_lock = asyncio.Lock()
_queue_task: Optional[asyncio.Task] = None  # strong ref so the queue task isn't garbage-collected


def set_model(whisper_model, name: Optional[str]):
    global model, model_name
    model = whisper_model
    model_name = name


def clear_all() -> Dict[str, int]:
    """Clear DB and delete temp uploads still waiting in the queue."""
    for path in db.pending_file_paths():
        if os.path.exists(path):
            os.remove(path)
    return db.clear_all()


async def add_task(file_paths: List[str], file_names: Optional[List[str]] = None) -> str:
    """Add a new task to the queue and start processing if not already running."""
    global _queue_task, is_running
    task = Task(file_paths, file_names)
    db.save_task(task)
    if not is_running:
        is_running = True  # set before scheduling so concurrent uploads don't start a second loop
        _queue_task = asyncio.create_task(_process_queue())
    return task.id


def get_task(task_id: str) -> Optional[Task]:
    return db.retrieve_task(task_id)


def get_file(task_id: str, file_index: int) -> Optional[TaskFile]:
    task = db.retrieve_task(task_id)
    return task.get_file(file_index) if task else None


def get_completed_results(task_id: str) -> Optional[Dict]:
    task = db.retrieve_task(task_id)
    if not task:
        return None
    completed = task.get_completed_files()
    return {
        "task_id": task_id,
        "completed_count": len(completed),
        "total_count": len(task.files),
        "results": [f.result_dict() for f in completed]
    }


def get_file_result(task_id: str, file_index: int) -> Optional[Dict]:
    file = get_file(task_id, file_index)
    return {"task_id": task_id, **file.result_dict()} if file and file.file_has_result() else None


def get_queue_info() -> Dict:
    current = db.retrieve_task(current_task_id) if current_task_id else None
    return {
        "queue_length": db.count_truly_pending_tasks(),
        "is_processing": current_task_id is not None,
        "current_task": current.json_response_format() if current else None
    }


async def _process_queue():
    """Process tasks in the queue one at a time."""
    global is_running, current_task_id
    try:
        while task := db.next_pending():
            current_task_id = task.id
            print(f"📋 Starting transcription for task {task.id} with model {model_name}")
            try:
                async with model_lock:
                    await _process_task(task)
                print(f"✅ Task {task.id} completed: {len(task.get_completed_files())} successful")
            except Exception as e:
                print(f"❌ Error processing task {task.id}: {e}")
                for file in task.files:
                    if file.status in (FileStatus.PENDING, FileStatus.PROCESSING):
                        file.fail(f"Task processing error: {e}")
                db.save_task(task)
            current_task_id = None
            await asyncio.sleep(0.5)
    except Exception as e:
        print(f"Error detected in queue processing: {e}")
    finally:
        is_running = False
        current_task_id = None
        print("✅ Queue processing completed")


async def _process_task(task: Task):
    """Transcribe each file in the task, saving status/results as we go."""
    global model, gpu
    loop = asyncio.get_running_loop()
    if model is None:  # lazy: first local transcription downloads/loads the model (caller holds model_lock)
        print(f"⬇️ Loading model {model_name} (first use, may download)...")
        model, gpu = await loop.run_in_executor(None, load_model, model_name, hw, gpu)
    for file in task.files:
        try:
            print(f'🔄 Starting file {file.file_index + 1}/{len(task.files)}: {file.file_name}')
            file.start_processing()
            db.save_task(task)  # Save immediately so frontend sees processing status
            text, language, duration = await loop.run_in_executor(None, _transcribe, file, task)
            file.complete(transcription=text, language=language, duration=duration)
            print(f"✅ File {file.file_name} completed, saved as {save_transcript(file.file_name, text)}")
        except Exception as e:
            print(f"❌ Error transcribing {file.file_name}: {e}")
            file.fail(str(e))
        finally:
            db.save_task(task)
            if os.path.exists(file.file_path):
                os.remove(file.file_path)


def _transcribe(file: TaskFile, task: Task):
    """Runs in a worker thread. Progress = end of last decoded segment / audio duration."""
    segments, info = model.transcribe(file.file_path, vad_filter=True)
    parts = []
    for seg in segments:  # generator: decoding happens lazily here
        parts.append(seg.text)
        pct = min(99, int(seg.end / info.duration * 100)) if info.duration else 0
        if pct > file.progress:
            file.progress = pct
            db.save_task(task)
    return "".join(parts).strip(), info.language, info.duration
