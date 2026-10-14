import os, asyncio
from .task_model import Task
from database.task_database import TaskDatabase


async def process_task(task: Task, model, model_name: str, db: TaskDatabase):
    """Transcribe each file in the task, saving status/results as we go."""
    total_files = len(task.files)
    loop = asyncio.get_running_loop()

    for file in task.files:
        try:
            print(f'🔄 Starting file {file.file_index + 1}/{total_files}: {file.file_name}')
            file.start_processing()
            db.add_task(task)  # Save immediately so frontend sees processing status

            text, language, duration = await loop.run_in_executor(
                None, _transcribe, model, file, task, db)
            file.complete(transcription=text, language=language, duration=duration)
            db.add_task(task)
            print(f"✅ File {file.file_name} completed")

        except Exception as e:
            print(f"❌ Error transcribing {file.file_name}: {e}")
            file.fail(str(e))
            db.add_task(task)

        finally:
            if os.path.exists(file.file_path):
                os.remove(file.file_path)

    print(f"🗂️ All files for task {task.id} processed")


def _transcribe(model, file, task: Task, db: TaskDatabase):
    """Runs in a worker thread. Progress = end of last decoded segment / audio duration."""
    segments, info = model.transcribe(file.file_path, vad_filter=True)
    parts = []
    for seg in segments:  # generator: decoding happens lazily here
        parts.append(seg.text)
        pct = min(99, int(seg.end / info.duration * 100)) if info.duration else 0
        if pct > file.progress:
            file.update_progress(pct)
            db.add_task(task)
    return "".join(parts).strip(), info.language, info.duration
