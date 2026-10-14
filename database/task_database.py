"""SQLite persistence for tasks and their files."""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from task_management.task_model import Task, TaskFile, FileStatus

DB_PATH = "tasks.db"
FILE_COLS = ("task_id, file_index, file_name, file_path, status, progress, transcription, "
             "language, duration, error_message, created_at, started_at, completed_at")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


with _conn() as c:
    c.executescript('''
        CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, created_at TEXT, file_count INTEGER);
        CREATE TABLE IF NOT EXISTS task_files (
            task_id TEXT, file_index INTEGER, file_name TEXT, file_path TEXT, status TEXT,
            progress INTEGER DEFAULT 0, transcription TEXT, language TEXT, duration REAL,
            error_message TEXT, created_at TEXT, started_at TEXT, completed_at TEXT,
            PRIMARY KEY (task_id, file_index), FOREIGN KEY (task_id) REFERENCES tasks (id));
        CREATE INDEX IF NOT EXISTS idx_task_files_status ON task_files (status);
    ''')


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _dt(s: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(s) if s else None


def save_task(task: Task) -> None:
    """Insert or update a task and all its files."""
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO tasks (id, created_at, file_count) VALUES (?, ?, ?)",
                  (task.id, task.created_at.isoformat(), len(task.files)))
        c.executemany(f"INSERT OR REPLACE INTO task_files ({FILE_COLS}) VALUES ({', '.join('?' * 13)})", [
            (f.task_id, f.file_index, f.file_name, f.file_path, f.status.value, f.progress,
             f.transcription, f.language, f.duration, f.error_message,
             f.created_at.isoformat(), _iso(f.started_at), _iso(f.completed_at))
            for f in task.files])


def retrieve_task(task_id: str) -> Optional[Task]:
    with _conn() as c:
        row = c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        task = Task([])
        task.id, task.created_at = row["id"], datetime.fromisoformat(row["created_at"])
        for r in c.execute("SELECT * FROM task_files WHERE task_id = ? ORDER BY file_index", (task_id,)):
            f = TaskFile(r["file_path"], r["file_index"], r["task_id"], r["file_name"])
            f.status = FileStatus(r["status"])
            f.progress, f.transcription, f.language = r["progress"], r["transcription"], r["language"]
            f.duration, f.error_message = r["duration"], r["error_message"]
            f.created_at = datetime.fromisoformat(r["created_at"])
            f.started_at, f.completed_at = _dt(r["started_at"]), _dt(r["completed_at"])
            task.files.append(f)
        return task


def next_pending() -> Optional[Task]:
    """Oldest task that still has a pending file."""
    with _conn() as c:
        row = c.execute("SELECT task_id FROM task_files WHERE status = ? ORDER BY created_at LIMIT 1",
                        (FileStatus.PENDING.value,)).fetchone()
    return retrieve_task(row[0]) if row else None


def count_truly_pending_tasks() -> int:
    """Count tasks where ALL files are still pending."""
    with _conn() as c:
        return c.execute('''
            SELECT COUNT(*) FROM (SELECT task_id FROM task_files GROUP BY task_id
                                  HAVING COUNT(*) = SUM(status = ?))
        ''', (FileStatus.PENDING.value,)).fetchone()[0]


def pending_file_paths() -> List[str]:
    """Temp paths of files not yet processed (processed files are already deleted)."""
    with _conn() as c:
        rows = c.execute("SELECT file_path FROM task_files WHERE status IN (?, ?)",
                         (FileStatus.PENDING.value, FileStatus.PROCESSING.value)).fetchall()
    return [r[0] for r in rows]


def clear_all() -> Dict[str, int]:
    """Clear all tasks and files. Returns counts of deleted records."""
    with _conn() as c:
        files = c.execute("DELETE FROM task_files").rowcount
        tasks = c.execute("DELETE FROM tasks").rowcount
    return {"deleted_tasks": tasks, "deleted_files": files}
