import tempfile
from pathlib import Path

from app.storage.db import Storage


def test_create_and_get_task():
    with tempfile.TemporaryDirectory() as tmp:
        db = Storage(db_path=Path(tmp) / "test.db")
        task_id = db.create_task("https://bilibili.com/video/BV123", "bilibili")
        task = db.get_task(task_id)
        assert task is not None
        assert task["url"] == "https://bilibili.com/video/BV123"
        assert task["status"] == "pending"


def test_update_task():
    with tempfile.TemporaryDirectory() as tmp:
        db = Storage(db_path=Path(tmp) / "test.db")
        task_id = db.create_task("https://bilibili.com/video/BV123", "bilibili")
        db.update_task(task_id, status="done", summary="test summary")
        task = db.get_task(task_id)
        assert task["status"] == "done"
        assert task["summary"] == "test summary"


def test_list_tasks():
    with tempfile.TemporaryDirectory() as tmp:
        db = Storage(db_path=Path(tmp) / "test.db")
        db.create_task("url1", "bilibili")
        db.create_task("url2", "bilibili")
        tasks = db.list_tasks()
        assert len(tasks) == 2


def test_delete_tasks():
    with tempfile.TemporaryDirectory() as tmp:
        db = Storage(db_path=Path(tmp) / "test.db")
        db.create_task("url1", "bilibili")
        db.create_task("url2", "bilibili")
        deleted = db.delete_tasks()
        assert deleted == 2
        assert db.task_count() == 0
