"""Integration tests: mock external deps, test full business flow via real HTTP."""
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


# Mock paths — target where the name is USED (imported), not where it's defined
MOCK_TRANSCRIBE = "app.core.pipeline.transcribe"
MOCK_DOWNLOAD = "app.platforms.bilibili.BilibiliPlatform.download"
MOCK_GET_LLM = "app.core.pipeline.get_llm"

# All modules that do `from app.core.config import settings`
SETTINGS_TARGETS = [
    "app.core.pipeline.settings",
    "app.storage.db.settings",
    "app.llm.claude.settings",
    "app.llm.openai_proto.settings",
]


def _mock_download(url, output_dir, keep_video=False):
    output_dir.mkdir(parents=True, exist_ok=True)
    from app.platforms.bilibili import BilibiliPlatform
    video_id = BilibiliPlatform().parse_url(url)
    audio_path = output_dir / f"{video_id}.wav"
    audio_path.write_bytes(b"fake audio")
    return audio_path, {"title": "Test Video", "duration": 120, "video_id": video_id}, None


def _mock_transcribe(audio_path, language="zh"):
    return "这是一段测试转录文本。"


def _make_mock_llm(summary_text="这是摘要", content_type="general"):
    """Create a mock LLM that returns the given summary and content type."""
    llm = MagicMock()
    llm.classify.return_value = {"summary": "test video", "type": content_type}
    llm.summarize.return_value = summary_text
    llm.summarize_multimodal.return_value = summary_text
    return llm


def _make_settings(tmp_dir):
    s = MagicMock()
    s.data_dir = Path(tmp_dir)
    s.cache_dir = Path(tmp_dir) / "cache"
    s.audio_dir = Path(tmp_dir) / "cache" / "audio"
    s.transcript_dir = Path(tmp_dir) / "cache" / "transcripts"
    s.frames_dir = Path(tmp_dir) / "cache" / "frames"
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
         patch(MOCK_GET_LLM, return_value=_make_mock_llm("这是摘要")):

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
         patch(MOCK_GET_LLM, return_value=_make_mock_llm("摘要")):

        client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV123"})
        time.sleep(1)

        r = client.get("/api/tasks")
        assert len(r.json()["tasks"]) >= 1


def test_status_transitions(client):
    statuses = []

    def track_download(url, output_dir, keep_video=False):
        statuses.append("downloading")
        return _mock_download(url, output_dir, keep_video)

    def track_transcribe(audio_path, language="zh"):
        statuses.append("transcribing")
        return _mock_transcribe(audio_path, language)

    llm = MagicMock()
    llm.classify.side_effect = lambda *a, **kw: (statuses.append("classifying"), {"summary": "", "type": "general"})[1]
    llm.summarize.side_effect = lambda *a, **kw: (statuses.append("summarizing"), "摘要")[1]

    with patch(MOCK_DOWNLOAD, side_effect=track_download), \
         patch(MOCK_TRANSCRIBE, side_effect=track_transcribe), \
         patch(MOCK_GET_LLM, return_value=llm):

        r = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV123"})
        _wait_done(client, r.json()["task_id"])

        assert statuses == ["downloading", "transcribing", "classifying", "summarizing"]


def test_pipeline_download_error(client):
    with patch(MOCK_DOWNLOAD, side_effect=ConnectionError("超时")):
        r = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV123"})
        data = _wait_done(client, r.json()["task_id"])
        assert data["status"] == "failed"
        assert "超时" in data["error"]


def test_pipeline_llm_error(client):
    llm = _make_mock_llm()
    llm.classify.side_effect = RuntimeError("API key invalid")

    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_GET_LLM, return_value=llm):

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
         patch(MOCK_GET_LLM, return_value=_make_mock_llm("OpenAI摘要")):

        r = client.post("/api/summarize", json={
            "url": "https://bilibili.com/video/BV123",
            "llm_provider": "openai",
        })
        data = _wait_done(client, r.json()["task_id"])
        assert data["status"] == "done"
        assert data["summary"] == "OpenAI摘要"


def test_cache_hit_skips_download(client):
    """Same video_id reuses cached audio/transcript, skips download and transcription."""
    download_count = 0
    transcribe_count = 0

    def counting_download(url, output_dir, keep_video=False):
        nonlocal download_count
        download_count += 1
        return _mock_download(url, output_dir, keep_video)

    def counting_transcribe(audio_path, language="zh"):
        nonlocal transcribe_count
        transcribe_count += 1
        return _mock_transcribe(audio_path, language)

    with patch(MOCK_DOWNLOAD, side_effect=counting_download), \
         patch(MOCK_TRANSCRIBE, side_effect=counting_transcribe), \
         patch(MOCK_GET_LLM, return_value=_make_mock_llm("摘要")):

        r1 = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV123"})
        _wait_done(client, r1.json()["task_id"])
        assert download_count == 1
        assert transcribe_count == 1

        r2 = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV123"})
        _wait_done(client, r2.json()["task_id"])
        assert download_count == 1
        assert transcribe_count == 1

        tasks = client.get("/api/tasks").json()["tasks"]
        assert len(tasks) == 2
        assert all(t["status"] == "done" for t in tasks)


def test_content_type_routing(client):
    """Classify returns 'tutorial' → summarize receives content_type='tutorial'."""
    llm = _make_mock_llm("教程摘要", content_type="tutorial")

    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_GET_LLM, return_value=llm):

        r = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV123"})
        _wait_done(client, r.json()["task_id"])

        llm.classify.assert_called_once()
        call_kwargs = llm.summarize.call_args
        assert call_kwargs[1].get("content_type") == "tutorial" or (len(call_kwargs[0]) > 3 and call_kwargs[0][3] == "tutorial")
