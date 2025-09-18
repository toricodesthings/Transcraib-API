from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict
import uuid, os

# Task status enumeration, 5 states available
class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    
class FileStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# Class data structure for individual files within a task
class TaskFile:
    """Class representing individual files within a transcription task (class Task)."""
    
    def __init__(self, file_path: str, file_index: int, task_id: str):
        self.file_path = file_path
        self.file_index = file_index
        self.task_id = task_id 
        self.file_name = os.path.basename(file_path)
        
        # File-specific state
        self.status = FileStatus.PENDING
        self.progress = 0 # Percentage progress for this file, settable
        
        # Result fields per file
        self.transcription = None
        self.language = None
        self.duration = None
        self.error_message = None
        
        # Timestamps
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
    
    def start_processing(self):
        self.status = FileStatus.PROCESSING
        self.progress = 0
        self.started_at = datetime.now()
        
    def update_progress(self, progress: int):
        self.progress = progress
    
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
    
    def json_response_format(self) -> Dict:
        """Convert file info to dictionary for API responses"""
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

# Class data structure for transcription tasks
class Task:
    """Task model class representing a whole transcription task."""
    
    # Initialize a new task with file paths and optional user ID (for now)
    def __init__(self, file_paths: List[str], user_id: Optional[str] = None):
        self.id = str(uuid.uuid4()) 
        self.user_id = user_id # Placeholder for future user association
        self.created_at = datetime.now()
        
        self.files = [TaskFile(path, i, self.id) for i, path in enumerate(file_paths)]
    
    def get_file(self, file_index: int) -> Optional[TaskFile]:
        if 0 <= file_index < len(self.files):
            return self.files[file_index]
        return None
    
    def get_completed_files(self) -> List[TaskFile]:
        return [f for f in self.files if f.file_has_result()]

    def get_failed_files(self) -> List[TaskFile]:
        return [f for f in self.files if f.status == FileStatus.FAILED]
    
    def get_in_progress_files(self) -> List[TaskFile]:
        return [f for f in self.files if f.status == FileStatus.PROCESSING]
    
    def get_pending_files(self) -> List[TaskFile]:
        return [f for f in self.files if f.status == FileStatus.PENDING]

    # Convert a task to dictionary format for API responses
    def json_response_format(self) -> Dict:
        """Convert task to dictionary for API responses"""
        
        # Calculate summary stats
        total_files = len(self.files)
        completed_files = len(self.get_completed_files())
        failed_files = len(self.get_failed_files())
        processing_files = len(self.get_in_progress_files())
        pending_files = len(self.get_pending_files())
        
        # Overall progress (average of all file progress)
        overall_progress = sum(f.progress for f in self.files) // total_files if total_files > 0 else 0
            
        # Determine overall status
        if completed_files + failed_files == total_files:
            overall_status = "completed" if completed_files > 0 else "failed"
        elif processing_files > 0 or completed_files > 0:
            overall_status = "processing"
        else:
            overall_status = "pending"
            
        return {
            "task_id": self.id,
            "created_at": self.created_at.isoformat(),
            
            # Summary for quick overview
            "summary": {
                "overall_status": overall_status,
                "overall_progress": overall_progress,
                "total_files": total_files,
                "completed": completed_files,
                "failed": failed_files,
                "processing": processing_files,
                "pending": pending_files
            },
            
            "files": [file.json_response_format() for file in self.files],
            "completed_results": [
                {
                    "file_index": f.file_index,
                    "file_name": f.file_name,
                    "transcription": f.transcription,
                    "language": f.language,
                    "duration": f.duration,
                    "completed_at": f.completed_at.isoformat()
                }
                for f in self.get_completed_files()
            ]
        }
    