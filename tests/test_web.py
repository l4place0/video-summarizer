"""Tests for Phase 02 — Web UI static file serving and frontend integration."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


SETTINGS_TARGETS = [
    "core.pipeline.settings",
    "core.storage.db.settings",
    "core.llm.claude.settings",
    "core.llm.openai_proto.settings",
]


def _make_settings(tmp_dir):
    s = MagicMock()
    s.data_dir = Path(tmp_dir)
    s.cache_dir = Path(tmp_dir) / "cache"
    s.audio_dir = Path(tmp_dir) / "cache" / "audio"
    s.transcript_dir = Path(tmp_dir) / "cache" / "transcripts"
    s.db_path = Path(tmp_dir) / "test.db"
    s.whisper_model = "base"
    s.llm_provider = "claude"
    s.llm_model = "test-model"
    s.anthropic_api_key = "test-key"
    s.openai_api_key = "test-key"
    s.openai_base_url = "http://test"
    s.anthropic_base_url = ""
    for d in [s.data_dir, s.cache_dir, s.audio_dir, s.transcript_dir]:
        d.mkdir(parents=True, exist_ok=True)
    return s


@pytest.fixture
def client(tmp_path):
    mock_s = _make_settings(tmp_path)
    patches = [patch(t, mock_s) for t in SETTINGS_TARGETS]

    for p in patches:
        p.start()

    import core.api.routes as routes
    from core.storage.db import Storage
    routes.db = Storage(db_path=tmp_path / "test.db")

    app = __import__("core.main", fromlist=["app"]).app
    yield TestClient(app)

    for p in patches:
        p.stop()


# --- Static file serving ---

def test_index_html_served(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Video Summarizer" in resp.text


def test_css_served(client):
    resp = client.get("/style.css")
    assert resp.status_code == 200
    assert "text/css" in resp.headers["content-type"]
    assert "--bg:" in resp.text


def test_js_served(client):
    resp = client.get("/app.js")
    assert resp.status_code == 200
    assert "javascript" in resp.headers["content-type"]
    assert "handleSubmit" in resp.text


# --- API routes NOT overridden by static mount ---

def test_health_still_works(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_api_tasks_still_works(client):
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    assert "tasks" in resp.json()


def test_api_storage_still_works(client):
    resp = client.get("/api/storage")
    assert resp.status_code == 200
    assert "db_size_bytes" in resp.json()


def test_api_summarize_still_works(client):
    resp = client.post("/api/summarize", json={"url": "https://youtube.com/x"})
    assert resp.status_code == 400  # invalid URL still rejected properly


# --- HTML content validation ---

def test_index_has_required_elements(client):
    html = client.get("/app.js")
    js = html.text

    # Verify key functions exist
    assert "handleSubmit" in js
    assert "pollTask" in js
    assert "loadHistory" in js
    assert "loadStorage" in js
    assert "handleCleanup" in js


def test_index_has_form_elements(client):
    html = client.get("/").text
    assert 'id="url-input"' in html
    assert 'id="language-select"' in html
    assert 'id="provider-select"' in html
    assert 'id="submit-btn"' in html
    assert 'id="history-table"' in html
    assert 'id="cleanup-btn"' in html
