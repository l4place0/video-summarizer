import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from core.storage.db import Storage


def _make_client(tmp_dir: str):
    """Create a test client with isolated storage."""
    with patch("core.api.routes.db") as mock_db, \
         patch("core.config.settings") as mock_settings:
        mock_settings.db_path = Path(tmp_dir) / "test.db"
        mock_settings.data_dir = Path(tmp_dir)
        mock_settings.cache_dir = Path(tmp_dir) / "cache"
        mock_settings.audio_dir = Path(tmp_dir) / "cache" / "audio"
        mock_settings.transcript_dir = Path(tmp_dir) / "cache" / "transcripts"

        real_db = Storage(db_path=Path(tmp_dir) / "test.db")
        mock_db.create_task = real_db.create_task
        mock_db.get_task = real_db.get_task
        mock_db.list_tasks = real_db.list_tasks
        mock_db.delete_tasks = real_db.delete_tasks
        mock_db.task_count = real_db.task_count
        mock_db.db_size = real_db.db_size
        mock_db.update_task = real_db.update_task

        from core.main import app
        yield TestClient(app), real_db


def test_health():
    with tempfile.TemporaryDirectory() as tmp:
        for client, _ in _make_client(tmp):
            resp = client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"


def test_summarize_invalid_url():
    with tempfile.TemporaryDirectory() as tmp:
        for client, _ in _make_client(tmp):
            resp = client.post("/api/summarize", json={"url": "https://youtube.com/watch?v=abc"})
            assert resp.status_code == 400


def test_tasks_empty():
    with tempfile.TemporaryDirectory() as tmp:
        for client, _ in _make_client(tmp):
            resp = client.get("/api/tasks")
            assert resp.status_code == 200
            assert resp.json()["tasks"] == []


def test_task_not_found():
    with tempfile.TemporaryDirectory() as tmp:
        for client, _ in _make_client(tmp):
            resp = client.get("/api/tasks/nonexistent")
            assert resp.status_code == 404
