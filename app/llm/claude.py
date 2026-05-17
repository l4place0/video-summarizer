import base64
import logging
import subprocess
import tempfile
from pathlib import Path

import anthropic

from app.core.config import settings
from app.llm.base import BaseLLM
from app.llm.prompts import get_summary_prompt

logger = logging.getLogger(__name__)


def _extract_frames(video_path: Path, max_frames: int = 10, interval: int = 30) -> list[Path]:
    """Extract key frames from video using ffmpeg. Returns list of JPEG paths."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="frames_"))
    fps_filter = f"fps=1/{interval}"
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", fps_filter,
        "-frames:v", str(max_frames),
        "-q:v", "2",
        str(tmp_dir / "frame_%04d.jpg"),
        "-y", "-hide_banner", "-loglevel", "error",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning("ffmpeg frame extraction failed: %s", result.stderr)
        return []
    return sorted(tmp_dir.glob("frame_*.jpg"))


class ClaudeLLM(BaseLLM):
    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        kwargs = {"api_key": settings.anthropic_api_key}
        if settings.anthropic_base_url:
            kwargs["base_url"] = settings.anthropic_base_url
        self.client = anthropic.Anthropic(**kwargs)

    def _chat(self, prompt: str, max_tokens: int = 4096) -> str:
        message = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    def _chat_multimodal(self, content: list[dict], max_tokens: int = 4096) -> str:
        message = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": content}],
        )
        return message.content[0].text

    def summarize(self, transcript: str, lang: str = "zh", detail: str = "normal", content_type: str | None = None) -> str:
        prompt = get_summary_prompt(content_type or "general", lang, multimodal=False).format(transcript=transcript)
        logger.info("Summarizing with Claude (%s, type=%s)", settings.claude_model, content_type)
        summary = self._chat(prompt, max_tokens=4096)
        logger.info("Summary done: %d chars", len(summary))
        return summary

    def summarize_multimodal(
        self, transcript: str, video_path: Path, lang: str = "zh", detail: str = "normal", content_type: str | None = None
    ) -> str:
        prompt = get_summary_prompt(content_type or "general", lang, multimodal=True).format(transcript=transcript)

        frames = _extract_frames(
            video_path,
            max_frames=settings.max_frames,
            interval=settings.frame_interval,
        )

        content: list[dict] = []
        for frame in frames:
            b64 = base64.b64encode(frame.read_bytes()).decode()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
            })
        content.append({"type": "text", "text": prompt})

        logger.info("Multimodal summarizing with Claude (%s, %d frames, type=%s)", settings.claude_model, len(frames), content_type)
        summary = self._chat_multimodal(content, max_tokens=4096)
        logger.info("Multimodal summary done: %d chars", len(summary))
        return summary
