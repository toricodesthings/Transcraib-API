"""SQLite database wrapper for task management and queue."""
import sqlite3
from typing import List, Optional, Dict
from datetime import datetime
from task_management.task_model import Task, TaskFile, FileStatus
class TaskDatabase:
    # Initialize the database and create tasks table if it doesn't exist
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        self._initialize_database()
    
    # Create tasks table
    def _initialize_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TEXT,
                    file_count INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_files (
                    task_id TEXT,
                    file_index INTEGER,
                    file_name TEXT,
                    file_path TEXT,
                    status TEXT,
                    progress INTEGER DEFAULT 0,
                    transcription TEXT,
                    language TEXT,
                    duration REAL,
                    error_message TEXT,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    PRIMARY KEY (task_id, file_index),
                    FOREIGN KEY (task_id) REFERENCES tasks (id)
                )
            ''')
            
            # Index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_task_files_status 
                ON task_files (status)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_task_files_task_id 
                ON task_files (task_id)
            ''')
            conn.commit()
    
    # Add OR update a task in the database with status and results
    def add_task(self, task: Task) -> None:
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert/update task record
            cursor.execute('''
                INSERT OR REPLACE INTO tasks (id, user_id, created_at, file_count)
                VALUES (?, ?, ?, ?)
            ''', (
                task.id,
                task.user_id,
                task.created_at.isoformat(),
                len(task.files)
            ))
            
                    # Insert/update all file records
            for file in task.files:
                cursor.execute('''
                    INSERT OR REPLACE INTO task_files (
                        task_id, file_index, file_name, file_path, status, progress,
                        transcription, language, duration, error_message,
                        created_at, started_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    file.task_id,
                    file.file_index,
                    file.file_name,
                    file.file_path,
                    file.status.value,
                    file.progress,
                    file.transcription,
                    file.language,
                    file.duration,
                    file.error_message,
                    file.created_at.isoformat(),
                    file.started_at.isoformat() if file.started_at else None,
                    file.completed_at.isoformat() if file.completed_at else None
                ))
            
            conn.commit()
            
    
    # Retrieve a task by task ID
    def retrieve_task(self, task_id: str) -> Optional[Task]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            task_row = cursor.fetchone()
                        
            if task_row:
                # Get all files for this task
                cursor.execute('''
                    SELECT * FROM task_files WHERE task_id = ? ORDER BY file_index
                ''', (task_id,))
                file_rows = cursor.fetchall()

                task = Task([], task_row[1])
                task.id = task_row[0]
                task.user_id = task_row[1]
                task.created_at = datetime.fromisoformat(task_row[2])
                
                # Reconstruct TaskFile objects
                task.files = []
                for row in file_rows:
                    file = TaskFile(row[3], row[1], row[0])
                    file.file_name = row[2]
                    file.status = FileStatus(row[4])
                    file.progress = row[5]
                    file.transcription = row[6]
                    file.language = row[7]
                    file.duration = row[8]
                    file.error_message = row[9]
                    file.created_at = datetime.fromisoformat(row[10])
                    file.started_at = datetime.fromisoformat(row[11]) if row[11] else None
                    file.completed_at = datetime.fromisoformat(row[12]) if row[12] else None
                    
                    task.files.append(file)

                return task
            
            return None
    
    def retrieve_pending(self) -> List[Task]:
        """Retrieve all tasks that have pending files."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Find tasks with any pending files
            cursor.execute('''
                SELECT DISTINCT task_id FROM task_files 
                WHERE status = ? 
                ORDER BY created_at
            ''', (FileStatus.PENDING.value,))
            
            task_ids = [row[0] for row in cursor.fetchall()]
            
            # Retrieve full task objects
            tasks = []
            for task_id in task_ids:
                task = self.retrieve_task(task_id)
                if task:
                    tasks.append(task)
            
            return tasks
        
    def get_completed_files(self, limit: int = 50) -> List[Dict]:
        """Get recently completed files across all tasks."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT task_id, file_index, filename, transcription, language, 
                       duration, completed_at
                FROM task_files 
                WHERE status = ? AND completed_at IS NOT NULL
                ORDER BY completed_at DESC
                LIMIT ?
            ''', (FileStatus.COMPLETED.value, limit))
            
            return [
                {
                    "task_id": row[0],
                    "file_index": row[1],
                    "filename": row[2],
                    "transcription": row[3],
                    "language": row[4],
                    "duration": row[5],
                    "completed_at": row[6]
                }
                for row in cursor.fetchall()
            ]
            
    # ADDED: Get file-level statistics
    def get_file_stats(self) -> Dict:
        """Get statistics about file processing."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            for status in FileStatus:
                cursor.execute('''
                    SELECT COUNT(*) FROM task_files WHERE status = ?
                ''', (status.value,))
                stats[status.value] = cursor.fetchone()[0]
            
            return {
                "file_counts": stats,
                "total_files": sum(stats.values())
            }
    
    # Count pending tasks (tasks with pending files)
    def count_pending(self) -> int:
        """Count tasks with pending files."""
        return len(self.retrieve_pending())
        
    # Clear all tasks from the database, for initialization or testing
    def clear_all(self) -> Dict[str, int]:
        """Clear all tasks and files from database. Returns counts of deleted records."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Count records before deletion
            cursor.execute('SELECT COUNT(*) FROM tasks')
            task_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM task_files')
            file_count = cursor.fetchone()[0]
            
            # Delete all records (files first due to foreign key)
            cursor.execute('DELETE FROM task_files')
            cursor.execute('DELETE FROM tasks')
            
            conn.commit()
            
            return {
                "deleted_tasks": task_count,
                "deleted_files": file_count
            }