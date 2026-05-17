"""Tests for multimodal pipeline — video path based summarization."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


# --- Multimodal LLM tests ---

def test_base_llm_multimodal_fallback():
    """BaseLLM.summarize_multimodal falls back to text-only."""
    from app.llm.base import BaseLLM

    class DummyLLM(BaseLLM):
        def _chat(self, prompt, max_tokens=4096):
            return f"text-only: {prompt[:20]}"

    llm = DummyLLM()
    with tempfile.TemporaryDirectory() as tmp:
        video = Path(tmp) / "test.mp4"
        video.write_bytes(b"fake video")
        result = llm.summarize_multimodal("hello", video, lang="zh", detail="normal")
    assert "text-only" in result


def test_base_llm_classify():
    """BaseLLM.classify parses JSON response."""
    from app.llm.base import BaseLLM

    class DummyLLM(BaseLLM):
        def _chat(self, prompt, max_tokens=4096):
            return '{"summary": "test video", "type": "tutorial"}'

    llm = DummyLLM()
    result = llm.classify("some transcript")
    assert result["type"] == "tutorial"
    assert result["summary"] == "test video"


def test_base_llm_classify_invalid_json():
    """BaseLLM.classify falls back to general on bad JSON."""
    from app.llm.base import BaseLLM

    class DummyLLM(BaseLLM):
        def _chat(self, prompt, max_tokens=4096):
            return "not json at all"

    llm = DummyLLM()
    result = llm.classify("some transcript")
    assert result["type"] == "general"


def test_base_llm_classify_markdown_json():
    """BaseLLM.classify handles markdown-wrapped JSON."""
    from app.llm.base import BaseLLM

    class DummyLLM(BaseLLM):
        def _chat(self, prompt, max_tokens=4096):
            return '```json\n{"summary": "test", "type": "demo"}\n```'

    llm = DummyLLM()
    result = llm.classify("some transcript")
    assert result["type"] == "demo"


def test_claude_multimodal_extracts_frames():
    """Claude multimodal extracts frames internally and sends as images."""
    from app.llm.claude import ClaudeLLM

    with tempfile.TemporaryDirectory() as tmp:
        video = Path(tmp) / "test.mp4"
        video.write_bytes(b"fake video")

        with patch("app.llm.claude.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.anthropic_base_url = ""
            mock_settings.claude_model = "test-model"
            mock_settings.max_frames = 5
            mock_settings.frame_interval = 30

            llm = ClaudeLLM()

            with patch.object(llm, "_chat_multimodal", return_value="multimodal summary") as mock_chat, \
                 patch("app.llm.claude._extract_frames") as mock_extract:
                frame = Path(tmp) / "frame.jpg"
                frame.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
                mock_extract.return_value = [frame]

                result = llm.summarize_multimodal("transcript text", video, lang="zh", content_type="general")

                assert result == "multimodal summary"
                mock_extract.assert_called_once()
                call_args = mock_chat.call_args
                content = call_args[0][0]
                assert len(content) == 2
                assert content[0]["type"] == "image"
                assert content[1]["type"] == "text"


def test_openai_multimodal_frame_first():
    """OpenAI multimodal tries frame extraction first."""
    from app.llm.openai_proto import OpenAILLM

    with tempfile.TemporaryDirectory() as tmp:
        video = Path(tmp) / "test.mp4"
        video.write_bytes(b"fake video")

        with patch("app.llm.openai_proto.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = "http://test"
            mock_settings.openai_model = "test-model"
            mock_settings.openai_vision_model = ""
            mock_settings.max_frames = 5
            mock_settings.frame_interval = 30

            llm = OpenAILLM()

            with patch.object(llm, "_chat_multimodal", return_value="frame summary") as mock_chat, \
                 patch("app.llm.openai_proto._extract_frames") as mock_extract:
                frame = Path(tmp) / "frame.jpg"
                frame.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
                mock_extract.return_value = [frame]

                result = llm.summarize_multimodal("transcript text", video, lang="zh", content_type="general")

                assert result == "frame summary"
                mock_extract.assert_called_once()
                call_args = mock_chat.call_args
                content = call_args[0][0]
                assert content[0]["type"] == "image_url"


def test_openai_multimodal_fallback_to_native_video():
    """OpenAI falls back to native video when frame extraction fails."""
    from app.llm.openai_proto import OpenAILLM

    with tempfile.TemporaryDirectory() as tmp:
        video = Path(tmp) / "test.mp4"
        video.write_bytes(b"fake video data")

        with patch("app.llm.openai_proto.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = "http://test"
            mock_settings.openai_model = "test-model"
            mock_settings.openai_vision_model = "mimo-v2-omni"
            mock_settings.max_frames = 5
            mock_settings.frame_interval = 30

            llm = OpenAILLM()

            with patch.object(llm, "_chat_multimodal", return_value="native video summary") as mock_chat, \
                 patch("app.llm.openai_proto._extract_frames", return_value=[]):

                result = llm.summarize_multimodal("transcript text", video, lang="zh", content_type="general")

                assert result == "native video summary"
                call_args = mock_chat.call_args
                content = call_args[0][0]
                assert content[0]["type"] == "video_url"


def test_openai_multimodal_fallback_to_text():
    """OpenAI falls back to text-only when both frame and native video fail."""
    from app.llm.openai_proto import OpenAILLM

    with tempfile.TemporaryDirectory() as tmp:
        video = Path(tmp) / "test.mp4"
        video.write_bytes(b"fake video data")

        with patch("app.llm.openai_proto.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = "http://test"
            mock_settings.openai_model = "test-model"
            mock_settings.openai_vision_model = "mimo-v2-omni"
            mock_settings.max_frames = 5
            mock_settings.frame_interval = 30

            llm = OpenAILLM()

            call_count = 0

            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise RuntimeError("API error")
                return "text fallback"

            with patch.object(llm, "_chat", side_effect=side_effect), \
                 patch.object(llm, "_chat_multimodal", side_effect=side_effect), \
                 patch("app.llm.openai_proto._extract_frames") as mock_extract:
                frame = Path(tmp) / "frame.jpg"
                frame.write_bytes(b"fake")
                mock_extract.return_value = [frame]

                result = llm.summarize_multimodal("transcript", video, lang="zh", content_type="general")

                assert result == "text fallback"


def test_content_type_routing():
    """content_type is passed through to prompt selection."""
    from app.llm.prompts import get_summary_prompt

    tutorial_prompt = get_summary_prompt("tutorial", "zh")
    general_prompt = get_summary_prompt("general", "zh")

    assert "步骤" in tutorial_prompt or "操作" in tutorial_prompt
    assert tutorial_prompt != general_prompt
    assert "{transcript}" in tutorial_prompt
    assert "{transcript}" in general_prompt


def test_content_types_coverage():
    """All content types have prompts."""
    from app.llm.prompts import CONTENT_TYPES, get_summary_prompt

    for ct in CONTENT_TYPES:
        prompt = get_summary_prompt(ct, "zh")
        assert "{transcript}" in prompt
        prompt_en = get_summary_prompt(ct, "en")
        assert "{transcript}" in prompt_en
