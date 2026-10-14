from collections import Counter
from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict
import uuid, os


class FileStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskFile:
    """An individual file within a transcription task."""

    def __init__(self, file_path: str, file_index: int, task_id: str, file_name: Optional[str] = None):
        self.file_path = file_path
        self.file_index = file_index
        self.task_id = task_id
        self.file_name = file_name or os.path.basename(file_path)
        self.status = FileStatus.PENDING
        self.progress = 0
        self.transcription = None
        self.language = None
        self.duration = None
        self.error_message = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None

    def start_processing(self):
        self.status = FileStatus.PROCESSING
        self.progress = 0
        self.started_at = datetime.now()

    def complete(self, transcription: str, language: str, duration: float):
        self.status = FileStatus.COMPLETED
        self.progress = 100
        self.transcription = transcription
        self.language = language
        self.duration = duration
        self.completed_at = datetime.now()

    def fail(self, error_message: str):
        self.status = FileStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()

    def file_has_result(self) -> bool:
        return self.status == FileStatus.COMPLETED and self.transcription is not None

    def result_dict(self) -> Dict:
        return {
            "file_index": self.file_index,
            "file_name": self.file_name,
            "transcription": self.transcription,
            "language": self.language,
            "duration": self.duration,
            "completed_at": self.completed_at.isoformat(),
        }

    def json_response_format(self) -> Dict:
        return {
            "file_index": self.file_index,
            "file_name": self.file_name,
            "status": self.status.value,
            "progress": self.progress,
            "error": self.error_message,
            "timestamps": {
                "created_at": self.created_at.isoformat(),
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None
            }
        }


class Task:
    """A whole transcription task (one upload batch)."""

    def __init__(self, file_paths: List[str], file_names: Optional[List[str]] = None):
        self.id = str(uuid.uuid4())
        self.created_at = datetime.now()
        names = file_names or [None] * len(file_paths)
        self.files = [TaskFile(path, i, self.id, name) for i, (path, name) in enumerate(zip(file_paths, names))]

    def get_file(self, file_index: int) -> Optional[TaskFile]:
        return self.files[file_index] if 0 <= file_index < len(self.files) else None

    def get_completed_files(self) -> List[TaskFile]:
        return [f for f in self.files if f.file_has_result()]

    def json_response_format(self) -> Dict:
        counts = Counter(f.status for f in self.files)
        total = len(self.files)
        completed, failed = len(self.get_completed_files()), counts[FileStatus.FAILED]
        processing, pending = counts[FileStatus.PROCESSING], counts[FileStatus.PENDING]

        if completed + failed == total:
            overall_status = "completed" if completed > 0 else "failed"
        elif processing > 0 or completed > 0:
            overall_status = "processing"
        else:
            overall_status = "pending"

        return {
            "task_id": self.id,
            "created_at": self.created_at.isoformat(),
            "summary": {
                "overall_status": overall_status,
                "overall_progress": sum(f.progress for f in self.files) // total if total else 0,
                "total_files": total,
                "completed": completed,
                "failed": failed,
                "processing": processing,
                "pending": pending
            },
            "files": [f.json_response_format() for f in self.files],
            "completed_results": [f.result_dict() for f in self.get_completed_files()]
        }
