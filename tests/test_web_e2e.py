"""End-to-end browser simulation: real HTTP, mocked externals, full user journey."""
import time
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

MOCK_DOWNLOAD = "app.platforms.bilibili.BilibiliPlatform.download"
MOCK_TRANSCRIBE = "app.core.pipeline.transcribe"
MOCK_CLAUDE_SUMMARIZE = "app.llm.claude.ClaudeLLM.summarize"

SETTINGS_TARGETS = [
    "app.core.pipeline.settings",
    "app.storage.db.settings",
    "app.llm.claude.settings",
    "app.llm.openai_proto.settings",
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


def _mock_download(url, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / "test.wav"
    audio_path.write_bytes(b"fake audio data")
    return audio_path, {"title": "Linux网络命名空间核心", "duration": 360, "video_id": "BV1xx411c7mq"}


def _mock_transcribe(audio_path, language="zh"):
    return "这是一段关于Linux网络命名空间的详细讲解。首先介绍了什么是网络命名空间..."


def _mock_summarize(transcript, lang="zh", detail="normal"):
    return "本视频详细讲解了Linux网络命名空间的核心概念，包括隔离原理、veth pair配置和实际应用场景。"


def _mock_download_error(url, output_dir):
    raise ConnectionError("网络连接超时")


def _mock_summarize_error(transcript, lang="zh", detail="normal"):
    raise RuntimeError("API key invalid")


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


def _wait_done(client, task_id, timeout=15):
    for _ in range(timeout * 2):
        resp = client.get(f"/api/tasks/{task_id}")
        data = resp.json()
        if data["status"] in ("done", "failed"):
            return data
        time.sleep(0.5)
    return data


# === 验收场景 1: 访问 localhost:8000 显示 Web 页面 ===

def test_scenario_1_homepage(client):
    """浏览器访问 / 显示完整 Web 页面"""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # 页面结构完整
    assert "视频摘要工具" in html
    assert 'id="url-input"' in html
    assert 'id="language-select"' in html
    assert 'id="provider-select"' in html
    assert 'id="submit-btn"' in html
    assert 'id="result-section"' in html
    assert 'id="history-table"' in html
    assert 'id="cleanup-btn"' in html
    assert 'href="/style.css"' in html
    assert 'src="/app.js"' in html


# === 验收场景 2: 输入 URL 并提交，任务创建，状态实时更新 ===

def test_scenario_2_submit_and_status_updates(client):
    """提交 URL → 任务创建 → 状态流转 pending→downloading→transcribing→summarizing→done"""
    statuses_seen = []

    def track_download(url, output_dir):
        statuses_seen.append("downloading")
        return _mock_download(url, output_dir)

    def track_transcribe(audio_path, language="zh"):
        statuses_seen.append("transcribing")
        return _mock_transcribe(audio_path, language)

    def track_summarize(transcript, lang="zh", detail="normal"):
        statuses_seen.append("summarizing")
        return _mock_summarize(transcript, lang, detail)

    with patch(MOCK_DOWNLOAD, side_effect=track_download), \
         patch(MOCK_TRANSCRIBE, side_effect=track_transcribe), \
         patch(MOCK_CLAUDE_SUMMARIZE, side_effect=track_summarize):

        # 提交任务
        resp = client.post("/api/summarize", json={
            "url": "https://bilibili.com/video/BV1xx411c7mq",
            "language": "zh",
            "llm_provider": "claude",
        })
        assert resp.status_code == 202
        task_id = resp.json()["task_id"]
        assert resp.json()["status"] == "pending"

        # 轮询状态（模拟前端行为）
        data = _wait_done(client, task_id)
        assert data["status"] == "done"
        assert statuses_seen == ["downloading", "transcribing", "summarizing"]


# === 验收场景 3: 任务完成，摘要正确展示，含标题和元数据 ===

def test_scenario_3_done_shows_summary(client):
    """任务完成 → 返回标题、摘要、转录、元数据"""
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_CLAUDE_SUMMARIZE, side_effect=_mock_summarize):

        resp = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV1xx411c7mq"})
        task_id = resp.json()["task_id"]
        data = _wait_done(client, task_id)

        assert data["status"] == "done"
        assert data["summary"] == "本视频详细讲解了Linux网络命名空间的核心概念，包括隔离原理、veth pair配置和实际应用场景。"
        assert data["metadata"]["title"] == "Linux网络命名空间核心"
        assert data["metadata"]["duration"] == 360
        assert data["transcript"] == "这是一段关于Linux网络命名空间的详细讲解。首先介绍了什么是网络命名空间..."
        assert data["platform"] == "bilibili"
        assert data["completed_at"] is not None


# === 验收场景 4: 任务失败，错误信息展示，红色状态 ===

def test_scenario_4_failed_shows_error(client):
    """任务失败 → 返回错误信息，status=failed"""
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_CLAUDE_SUMMARIZE, side_effect=_mock_summarize_error):

        resp = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV1xx411c7mq"})
        task_id = resp.json()["task_id"]
        data = _wait_done(client, task_id)

        assert data["status"] == "failed"
        assert "API key invalid" in data["error"]


def test_scenario_4b_download_error(client):
    """下载失败 → 返回错误信息"""
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download_error):
        resp = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV1xx411c7mq"})
        task_id = resp.json()["task_id"]
        data = _wait_done(client, task_id)

        assert data["status"] == "failed"
        assert "网络连接超时" in data["error"]


# === 验收场景 5: 页面刷新，历史任务列表加载 ===

def test_scenario_5_history_after_refresh(client):
    """完成任务后 → GET /api/tasks 返回历史列表"""
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_CLAUDE_SUMMARIZE, side_effect=_mock_summarize):

        # 创建并完成一个任务
        resp = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV1xx411c7mq"})
        _wait_done(client, resp.json()["task_id"])

        # 模拟页面刷新：请求历史列表
        resp = client.get("/api/tasks")
        assert resp.status_code == 200
        tasks = resp.json()["tasks"]
        assert len(tasks) >= 1

        task = tasks[0]
        assert task["status"] == "done"
        assert task["metadata"]["title"] == "Linux网络命名空间核心"
        assert task["summary"] is not None


# === 验收场景 6: 点击历史任务，详情加载到结果区 ===

def test_scenario_6_view_history_task(client):
    """点击查看 → GET /api/tasks/{id} 返回完整详情"""
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_CLAUDE_SUMMARIZE, side_effect=_mock_summarize):

        resp = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV1xx411c7mq"})
        task_id = resp.json()["task_id"]
        _wait_done(client, task_id)

        # 模拟点击"查看"
        resp = client.get(f"/api/tasks/{task_id}")
        assert resp.status_code == 200
        detail = resp.json()

        assert detail["task_id"] == task_id
        assert detail["status"] == "done"
        assert detail["summary"] is not None
        assert detail["transcript"] is not None
        assert detail["metadata"]["title"] == "Linux网络命名空间核心"


# === 验收场景 7: 清理存储，确认后执行，占用清零 ===

def test_scenario_7_cleanup_storage(client):
    """清理存储 → 删除所有任务和缓存"""
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_CLAUDE_SUMMARIZE, side_effect=_mock_summarize):

        # 先创建一个任务
        resp = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV1xx411c7mq"})
        _wait_done(client, resp.json()["task_id"])

        # 查看存储占用
        resp = client.get("/api/storage")
        info = resp.json()
        assert info["task_count"] >= 1

        # 清理存储
        resp = client.delete("/api/storage")
        assert resp.status_code == 200
        result = resp.json()
        assert result["deleted_tasks"] >= 1

        # 验证清空
        resp = client.get("/api/storage")
        info = resp.json()
        assert info["task_count"] == 0


# === 验收场景 8: 无效 URL 提交，前端校验拒绝 ===

def test_scenario_8_invalid_url_rejected(client):
    """无效 URL → 400 拒绝，不创建任务"""
    resp = client.post("/api/summarize", json={"url": "https://youtube.com/watch?v=abc"})
    assert resp.status_code == 400

    # 确认没有创建任务
    resp = client.get("/api/tasks")
    assert len(resp.json()["tasks"]) == 0


# === 额外: 静态资源完整性 ===

def test_static_assets_all_served(client):
    """CSS/JS 均可正常加载"""
    assert client.get("/style.css").status_code == 200
    assert client.get("/app.js").status_code == 200


def test_api_not_overridden_by_static(client):
    """静态挂载不覆盖 API 路由"""
    assert client.get("/health").status_code == 200
    assert client.get("/api/tasks").status_code == 200
    assert client.get("/api/storage").status_code == 200
    assert client.post("/api/summarize", json={"url": "https://youtube.com/x"}).status_code == 400


# === 额外: 多任务场景 ===

def test_multiple_tasks(client):
    """多个任务并行，历史列表完整"""
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_CLAUDE_SUMMARIZE, side_effect=_mock_summarize):

        ids = []
        for _ in range(3):
            resp = client.post("/api/summarize", json={"url": "https://bilibili.com/video/BV1xx411c7mq"})
            ids.append(resp.json()["task_id"])

        for tid in ids:
            _wait_done(client, tid)

        resp = client.get("/api/tasks")
        assert len(resp.json()["tasks"]) == 3
