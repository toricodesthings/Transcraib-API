"""SQLite database wrapper for task management and queue."""
import sqlite3, json
from typing import List, Optional
from task_management.task_model import Task, TaskStatus

class TaskDatabase:
    # Initialize the database and create tasks table if it doesn't exist
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        self._initialize_database()
    
    # Create tasks table
    def _initialize_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    status TEXT,
                    file_paths TEXT,
                    progress INTEGER DEFAULT 0,
                    results TEXT,
                    error_message TEXT,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT
                )
            """)
            conn.commit()
    
    # Add OR update a task in the database with status and results
    def add_task(self, task: Task):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tasks (id, user_id, status, file_paths, progress, results, error_message, created_at, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task.id, 
                task.user_id, 
                task.status.value, 
                json.dumps(task.file_paths), 
                task.progress, 
                json.dumps(task.results),
                task.error_message,
                task.created_at.isoformat(),
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None
            ))
            conn.commit()
    
    # Retrieve a task by task ID
    def retrieve_task(self, task_id: str) -> Optional[Task]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            
            if row:
                task = Task(file_paths=json.loads(row[3]), user_id=row[1])
                task.id = row[0]
                task.status = TaskStatus(row[2])
                task.progress = row[4]
                task.results = json.loads(row[5]) if row[5] else []
                task.error_message = row[6]
                return task
            
            return None
    
    # Retrieve all pending tasks ordered by creation time
    def retrieve_pending(self) -> List[Task]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM tasks WHERE status = ? ORDER BY created_at ASC", (TaskStatus.PENDING.value,))
            tasks_ids  = [row[0] for row in cursor.fetchall()]
            return [self.retrieve_task(task_id) for task_id in tasks_ids]
    
    # Count number of pending tasks
    def count_pending(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = ?", (TaskStatus.PENDING.value,))
            count = cursor.fetchone()[0]
            return count
        
    # Clear all tasks from the database, for initialization or testing
    def clear_all(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM tasks")
            task_count = cursor.fetchone()[0]
            
            conn.execute("DELETE FROM tasks")
            conn.commit()
            
            return task_count