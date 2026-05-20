"""Tests for Whisper ASR module, including CUDA OOM fallback."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_cuda_oom_fallback(monkeypatch):
    """CUDA OOM triggers permanent fallback to CPU."""
    import core.asr.whisper as w

    # Reset module state
    monkeypatch.setattr(w, "_device", "cuda")
    monkeypatch.setattr(w, "_model", None)
    monkeypatch.setattr(w, "_backend", "openai")

    mock_model = MagicMock()
    call_count = {"n": 0}

    def mock_transcribe(audio_path, language=None, fp16=False):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("CUDA out of memory. Tried to allocate...")
        return {"text": "fallback transcript"}

    mock_model.transcribe = mock_transcribe

    monkeypatch.setattr(w, "_get_model", lambda: mock_model)

    result = w.transcribe(Path("test.wav"), language="zh")
    assert result == "fallback transcript"
    assert w._device == "cpu"  # permanently switched
    assert call_count["n"] == 2  # tried once, then retried


def test_non_oom_error_reraised(monkeypatch):
    """Non-OOM RuntimeError is re-raised, not caught."""
    import core.asr.whisper as w

    monkeypatch.setattr(w, "_device", "cuda")
    monkeypatch.setattr(w, "_model", None)
    monkeypatch.setattr(w, "_backend", "openai")

    mock_model = MagicMock()
    mock_model.transcribe.side_effect = RuntimeError("Some other error")

    monkeypatch.setattr(w, "_get_model", lambda: mock_model)

    with pytest.raises(RuntimeError, match="Some other error"):
        w.transcribe(Path("test.wav"), language="zh")


def test_cpu_error_not_caught(monkeypatch):
    """RuntimeError on CPU is not caught (no CUDA OOM fallback)."""
    import core.asr.whisper as w

    monkeypatch.setattr(w, "_device", "cpu")
    monkeypatch.setattr(w, "_model", None)
    monkeypatch.setattr(w, "_backend", "openai")

    mock_model = MagicMock()
    mock_model.transcribe.side_effect = RuntimeError("out of memory")

    monkeypatch.setattr(w, "_get_model", lambda: mock_model)

    with pytest.raises(RuntimeError, match="out of memory"):
        w.transcribe(Path("test.wav"), language="zh")
