import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import settings

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id    TEXT PRIMARY KEY,
    url        TEXT NOT NULL,
    platform   TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'pending',
    summary    TEXT,
    transcript TEXT,
    metadata   TEXT,
    error      TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
"""


class Storage:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or settings.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def create_task(self, url: str, platform: str) -> str:
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO tasks (task_id, url, platform, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
            (task_id, url, platform, now),
        )
        self._conn.commit()
        return task_id

    def update_task(self, task_id: str, **fields) -> None:
        if not fields:
            return
        # Serialize dicts/lists to JSON for SQLite
        for k, v in fields.items():
            if isinstance(v, (dict, list)):
                fields[k] = json.dumps(v, ensure_ascii=False)
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values())
        vals.append(task_id)
        self._conn.execute(f"UPDATE tasks SET {sets} WHERE task_id = ?", vals)
        self._conn.commit()

    def get_task(self, task_id: str) -> dict | None:
        row = self._conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_tasks(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def delete_tasks(self, older_than_days: int | None = None) -> int:
        if older_than_days is not None:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
            cur = self._conn.execute("DELETE FROM tasks WHERE created_at < ?", (cutoff,))
        else:
            cur = self._conn.execute("DELETE FROM tasks")
        self._conn.commit()
        return cur.rowcount

    def find_cached_task(self, video_id: str) -> dict | None:
        """Find a completed task with the same video_id for cache reuse."""
        rows = self._conn.execute(
            "SELECT * FROM tasks WHERE status = 'done' ORDER BY created_at DESC"
        ).fetchall()
        for row in rows:
            d = self._row_to_dict(row)
            meta = d.get("metadata")
            if isinstance(meta, dict) and meta.get("video_id") == video_id:
                return d
        return None

    def task_count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]

    def db_size(self) -> int:
        return self.db_path.stat().st_size if self.db_path.exists() else 0

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        d = dict(row)
        if d.get("metadata"):
            d["metadata"] = json.loads(d["metadata"])
        return d
