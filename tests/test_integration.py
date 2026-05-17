"""Integration tests: mock external deps, test full business flow via real HTTP."""
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


# Mock paths — target where the name is USED (imported), not where it's defined
MOCK_TRANSCRIBE = "app.core.pipeline.transcribe"
MOCK_DOWNLOAD = "app.platforms.bilibili.BilibiliPlatform.download"
MOCK_CLAUDE_SUMMARIZE = "app.llm.claude.ClaudeLLM.summarize"
MOCK_OPENAI_SUMMARIZE = "app.llm.openai_proto.OpenAILLM.summarize"

# All modules that do `from app.core.config import settings`
SETTINGS_TARGETS = [
    "app.core.pipeline.settings",
    "app.storage.db.settings",
    "app.llm.claude.settings",
    "app.llm.openai_proto.settings",
]


def _mock_download(url, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "test.wav"
    audio_path.write_bytes(b"fake audio")
    return audio_path, {"title": "Test Video", "duration": 120, "video_id": "BV123"}


def _mock_transcribe(audio_path, language="zh"):
    return "这是一段测试转录文本。"


def _make_summarize(summary_text):
    def _summarize(self, transcript, lang="zh", detail="normal"):
        return summary_text
    return _summarize


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


def _wait_done(client, task_id, timeout=10):
    for _ in range(timeout * 2):
        resp = client.get(f"/api/tasks/{task_id}")
        data = resp.json()
        if data["status"] in ("done", "failed"):
            return data
        time.sleep(0.5)
    return data


@pytest.fixture
def client(tmp_path):
    mock_s = _make_settings(tmp_path)
    patches = [patch(t, mock_s) for t in SETTINGS_TARGETS]

    for p in patches:
        p.start()

    import app.api.routes as routes
    from app.storage.db import Storage
    routes.db = Storage(db_path=tmp_path / "test.db")

    app = __import__("app.main", fromlist=["app"]).app
    yield TestClient(app)

    for p in patches:
        p.stop()


# --- Tests ---

def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_invalid_url_400(client):
    r = client.post("/api/summarize", json={"url": "https://youtube.com/x"})
    assert r.status_code == 400


def test_full_pipeline_happy_path(client):
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_CLAUDE_SUMMARIZE, _make_summarize("这是摘要")):

        r = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV123"})
        assert r.status_code == 202
        task_id = r.json()["task_id"]

        data = _wait_done(client, task_id)
        assert data["status"] == "done", f"got {data['status']}: {data.get('error')}"
        assert data["summary"] == "这是摘要"
        assert data["metadata"]["title"] == "Test Video"
        assert data["transcript"] == "这是一段测试转录文本。"


def test_task_list(client):
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_CLAUDE_SUMMARIZE, _make_summarize("摘要")):

        client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV123"})
        time.sleep(1)

        r = client.get("/api/tasks")
        assert len(r.json()["tasks"]) >= 1


def test_status_transitions(client):
    statuses = []

    def track_download(url, output_dir):
        statuses.append("downloading")
        return _mock_download(url, output_dir)

    def track_transcribe(audio_path, language="zh"):
        statuses.append("transcribing")
        return _mock_transcribe(audio_path, language)

    def track_summarize(transcript, lang="zh", detail="normal"):
        statuses.append("summarizing")
        return "摘要"

    with patch(MOCK_DOWNLOAD, side_effect=track_download), \
         patch(MOCK_TRANSCRIBE, side_effect=track_transcribe), \
         patch(MOCK_CLAUDE_SUMMARIZE, side_effect=track_summarize):

        r = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV123"})
        _wait_done(client, r.json()["task_id"])

        assert statuses == ["downloading", "transcribing", "summarizing"]


def test_pipeline_download_error(client):
    with patch(MOCK_DOWNLOAD, side_effect=ConnectionError("超时")):
        r = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV123"})
        data = _wait_done(client, r.json()["task_id"])
        assert data["status"] == "failed"
        assert "超时" in data["error"]


def test_pipeline_llm_error(client):
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_CLAUDE_SUMMARIZE, side_effect=RuntimeError("API key invalid")):

        r = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV123"})
        data = _wait_done(client, r.json()["task_id"])
        assert data["status"] == "failed"
        assert "API key invalid" in data["error"]


def test_storage_query_and_cleanup(client):
    r = client.get("/api/storage")
    assert r.status_code == 200
    assert "db_size_bytes" in r.json()

    r = client.delete("/api/storage")
    assert r.status_code == 200
    assert "deleted_files" in r.json()


def test_task_not_found(client):
    assert client.get("/api/tasks/nonexist").status_code == 404


def test_openai_provider(client):
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_OPENAI_SUMMARIZE, _make_summarize("OpenAI摘要")):

        r = client.post("/api/summarize", json={
            "url": "https://bilibili.com/video/BV123",
            "llm_provider": "openai",
        })
        data = _wait_done(client, r.json()["task_id"])
        assert data["status"] == "done"
        assert data["summary"] == "OpenAI摘要"
