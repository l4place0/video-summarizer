"""Tests for Skill wrapper scripts."""
import os
import socket
import subprocess
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import uvicorn

SCRIPTS_DIR = Path(__file__).parent.parent / ".claude" / "skills" / "video-summarizer" / "scripts"
SUMMARIZE = str(SCRIPTS_DIR / "summarize.sh")
STATUS = str(SCRIPTS_DIR / "status.sh")

SETTINGS_TARGETS = [
    "app.core.pipeline.settings",
    "app.storage.db.settings",
    "app.llm.claude.settings",
    "app.llm.openai_proto.settings",
]

MOCK_DOWNLOAD = "app.platforms.bilibili.BilibiliPlatform.download"
MOCK_TRANSCRIBE = "app.core.pipeline.transcribe"
MOCK_GET_LLM = "app.core.pipeline.get_llm"


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


def _mock_download(url, output_dir, keep_video=False):
    output_dir.mkdir(parents=True, exist_ok=True)
    from app.platforms.bilibili import BilibiliPlatform
    video_id = BilibiliPlatform().parse_url(url)
    audio_path = output_dir / f"{video_id}.wav"
    audio_path.write_bytes(b"fake audio data")
    return audio_path, {"title": "Test Video Title", "duration": 125, "video_id": video_id}, None


def _mock_transcribe(audio_path, language="zh"):
    return "这是一段测试转录文本内容。"


def _make_mock_llm(summary="这是一个测试视频摘要。"):
    llm = MagicMock()
    llm.classify.return_value = {"summary": "test", "type": "general"}
    llm.summarize.return_value = summary
    llm.summarize_multimodal.return_value = summary
    return llm


def _free_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _run(cmd, env_vars=None, timeout=30):
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=env
    )


@pytest.fixture
def server(tmp_path):
    """Start a real uvicorn server in a background thread."""
    mock_s = _make_settings(tmp_path)
    patches = [patch(t, mock_s) for t in SETTINGS_TARGETS]
    for p in patches:
        p.start()

    import app.api.routes as routes
    from app.storage.db import Storage
    routes.db = Storage(db_path=tmp_path / "test.db")

    app = __import__("app.main", fromlist=["app"]).app

    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    srv = uvicorn.Server(config)
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}"
    for _ in range(30):
        try:
            subprocess.run(["curl", "-sf", f"{url}/health"], capture_output=True, timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    yield url

    srv.should_exit = True
    for p in patches:
        p.stop()


# === summarize.sh tests ===

def test_summarize_no_service():
    r = _run(
        f"bash {SUMMARIZE} https://bilibili.com/video/BV123",
        env_vars={"VIDEO_SUMMARIZER_URL": "http://127.0.0.1:19999"},
        timeout=15,
    )
    assert r.returncode == 1
    assert "未运行" in r.stdout


def test_summarize_no_args():
    r = _run(f"bash {SUMMARIZE}")
    assert r.returncode == 1
    assert "Usage" in r.stdout or "Usage" in r.stderr


def test_summarize_invalid_url(server):
    r = _run(
        f"bash {SUMMARIZE} https://youtube.com/watch?v=abc",
        env_vars={"VIDEO_SUMMARIZER_URL": server},
    )
    assert r.returncode == 1


def test_summarize_no_poll(server, tmp_path):
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_GET_LLM, return_value=_make_mock_llm()):

        r = _run(
            f"bash {SUMMARIZE} https://bilibili.com/video/BV123 --no-poll",
            env_vars={"VIDEO_SUMMARIZER_URL": server},
            timeout=10,
        )
        assert r.returncode == 0
        assert "任务已创建" in r.stdout
        lines = r.stdout.strip().split("\n")
        task_id = lines[-1]
        assert len(task_id) == 36


def test_summarize_full_flow(server):
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_GET_LLM, return_value=_make_mock_llm()):

        r = _run(
            f"bash {SUMMARIZE} https://bilibili.com/video/BV123",
            env_vars={"VIDEO_SUMMARIZER_URL": server},
            timeout=60,
        )
        assert r.returncode == 0
        assert "视频摘要完成" in r.stdout
        assert "Test Video Title" in r.stdout
        assert "这是一个测试视频摘要" in r.stdout
        assert "转录原文" in r.stdout


def test_summarize_with_options(server):
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_GET_LLM, return_value=_make_mock_llm()):

        r = _run(
            f"bash {SUMMARIZE} https://bilibili.com/video/BV123 --lang en --provider openai --detail brief --no-poll",
            env_vars={"VIDEO_SUMMARIZER_URL": server},
            timeout=10,
        )
        assert r.returncode == 0
        assert "任务已创建" in r.stdout


# === status.sh tests ===

def test_status_no_service():
    r = _run(
        f"bash {STATUS}",
        env_vars={"VIDEO_SUMMARIZER_URL": "http://127.0.0.1:19999"},
        timeout=15,
    )
    assert r.returncode == 1
    assert "未运行" in r.stdout


def test_status_running(server):
    r = _run(f"bash {STATUS}", env_vars={"VIDEO_SUMMARIZER_URL": server}, timeout=10)
    assert r.returncode == 0
    assert "运行中" in r.stdout
    assert "存储" in r.stdout


def test_status_with_tasks(server):
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_GET_LLM, return_value=_make_mock_llm()):

        _run(
            f"bash {SUMMARIZE} https://bilibili.com/video/BV123 --no-poll",
            env_vars={"VIDEO_SUMMARIZER_URL": server},
            timeout=10,
        )
        time.sleep(3)

        r = _run(f"bash {STATUS}", env_vars={"VIDEO_SUMMARIZER_URL": server}, timeout=10)
        assert r.returncode == 0
        assert "最近任务" in r.stdout


def test_status_task_detail(server):
    with patch(MOCK_DOWNLOAD, side_effect=_mock_download), \
         patch(MOCK_TRANSCRIBE, side_effect=_mock_transcribe), \
         patch(MOCK_GET_LLM, return_value=_make_mock_llm()):

        r = _run(
            f"bash {SUMMARIZE} https://bilibili.com/video/BV123 --no-poll",
            env_vars={"VIDEO_SUMMARIZER_URL": server},
            timeout=10,
        )
        task_id = r.stdout.strip().split("\n")[-1]
        time.sleep(3)

        r = _run(
            f"bash {STATUS} --task {task_id}",
            env_vars={"VIDEO_SUMMARIZER_URL": server},
            timeout=10,
        )
        assert r.returncode == 0
        assert "Test Video Title" in r.stdout or "任务ID" in r.stdout


def test_status_cleanup(server):
    r = _run(f"bash {STATUS} --cleanup", env_vars={"VIDEO_SUMMARIZER_URL": server}, timeout=10)
    assert r.returncode == 0
    assert "已删除" in r.stdout


def test_status_task_not_found(server):
    r = _run(
        f"bash {STATUS} --task nonexistent",
        env_vars={"VIDEO_SUMMARIZER_URL": server},
        timeout=10,
    )
    assert r.returncode == 1
    assert "不存在" in r.stdout
