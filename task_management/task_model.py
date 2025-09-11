from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict
import uuid

# Task status enumeration, 5 states available
class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

# Class data structure for transcription tasks
class Task:
    """Task model class representing a transcription task."""
    
    # Initialize a new task with file paths and optional user ID (for now)
    def __init__(self, file_paths: List[str], user_id: Optional[str] = None):
        self.id = str(uuid.uuid4()) 
        self.file_paths = file_paths
        self.user_id = user_id # Placeholder for future user association
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.results = [] 
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.error_message = None
    
    # Convert a task to dictionary format for API responses
    def response_format(self) -> Dict:
        """Convert task to dictionary for API responses"""
        return {
            "task_id": self.id,
            "status": self.status.value,
            "progress": self.progress,
            "file_count": len(self.file_paths),
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": self.results,
            "error_message": self.error_message
        }
    
    # Methods to update task status
    def start_processing(self):
        self.status = TaskStatus.PROCESSING
        self.progress = 10
        self.started_at = datetime.now()
        
    def in_progress(self, progress: int):
        self.progress = progress
        self.status = TaskStatus.IN_PROGRESS
    
    # Mark task as completed with results
    def complete(self, results: List[Dict]):
        self.status = TaskStatus.COMPLETED
        self.results = results
        self.progress = 100
        self.completed_at = datetime.now()
    
    # Mark task as failed with error message
    def fail(self, error_message: str):
        self.status = TaskStatus.FAILED
        self.results = [{"error": error_message}]
        self.completed_at = datetime.now()