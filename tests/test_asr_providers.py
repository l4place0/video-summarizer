"""Tests for ASR providers."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_base_asr_interface():
    from core.asr.base import BaseASR
    assert hasattr(BaseASR, "transcribe")


def test_inprocess_asr_duck_typing():
    from core.asr.whisper import InProcessASR
    asr = InProcessASR()
    assert hasattr(asr, "transcribe")


@patch("core.asr.local.httpx")
def test_local_asr_calls_endpoint(mock_httpx, tmp_path):
    from core.asr.local import LocalASR

    # Create a fake audio file
    audio = tmp_path / "test.wav"
    audio.write_bytes(b"fake audio data")

    # Mock httpx.post
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"transcript": "[00:00] Hello world"}
    mock_resp.raise_for_status = MagicMock()
    mock_httpx.post.return_value = mock_resp

    asr = LocalASR(endpoint="http://localhost:8001")
    result = asr.transcribe(audio, language="zh")

    assert result == "[00:00] Hello world"
    mock_httpx.post.assert_called_once()
    call_kwargs = mock_httpx.post.call_args
    assert "http://localhost:8001/transcribe" in call_kwargs[0][0]


@patch("core.asr.cloud.OpenAI")
def test_openai_whisper_api_calls_openai(mock_openai_cls, tmp_path):
    from core.asr.cloud import OpenAIWhisperAPI

    audio = tmp_path / "test.wav"
    audio.write_bytes(b"fake audio data")

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Hello world from cloud"
    mock_client.audio.transcriptions.create.return_value = mock_resp
    mock_openai_cls.return_value = mock_client

    asr = OpenAIWhisperAPI(api_key="test-key")
    result = asr.transcribe(audio, language="zh")

    assert result == "Hello world from cloud"
    mock_client.audio.transcriptions.create.assert_called_once()


def test_get_asr_inprocess():
    from core.asr import get_asr
    from core.asr.whisper import InProcessASR
    asr = get_asr("inprocess")
    assert isinstance(asr, InProcessASR)


def test_get_asr_local_requires_endpoint():
    from core.asr import get_asr
    with pytest.raises(ValueError, match="ASR_ENDPOINT"):
        get_asr("local")


def test_get_asr_openai_requires_key():
    from core.asr import get_asr
    with pytest.raises(ValueError, match="ASR_API_KEY"):
        get_asr("openai")
