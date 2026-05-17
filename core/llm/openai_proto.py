import base64
import logging
import subprocess
import tempfile
from pathlib import Path

from openai import OpenAI

from core.config import settings
from core.llm.base import BaseLLM
from core.llm.prompts import get_summary_prompt

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


class OpenAILLM(BaseLLM):
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    def _chat(self, prompt: str, max_tokens: int = 4096) -> str:
        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def _chat_multimodal(self, content: list[dict], max_tokens: int = 4096) -> str:
        model = settings.openai_vision_model or settings.openai_model
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def summarize(self, transcript: str, lang: str = "zh", detail: str = "normal", content_type: str | None = None) -> str:
        prompt = get_summary_prompt(content_type or "general", lang, multimodal=False).format(transcript=transcript)
        logger.info("Summarizing with OpenAI (%s, type=%s)", settings.openai_model, content_type)
        summary = self._chat(prompt, max_tokens=4096)
        logger.info("Summary done: %d chars", len(summary))
        return summary

    def summarize_multimodal(
        self, transcript: str, video_path: Path, lang: str = "zh", detail: str = "normal", content_type: str | None = None
    ) -> str:
        # Strategy 1: Extract frames and send as images (primary)
        try:
            return self._summarize_with_frames(transcript, video_path, lang, content_type)
        except Exception as e:
            logger.warning("Frame-based summarization failed: %s, trying native video", e)

        # Strategy 2: Native video via video_url (fallback)
        try:
            return self._summarize_native_video(transcript, video_path, lang, content_type)
        except Exception as e:
            logger.warning("Native video summarization failed: %s, falling back to text-only", e)

        # Strategy 3: Text-only (final fallback)
        return self.summarize(transcript, lang, content_type=content_type)

    def _summarize_native_video(self, transcript: str, video_path: Path, lang: str, content_type: str | None) -> str:
        prompt = get_summary_prompt(content_type or "general", lang, multimodal=True).format(transcript=transcript)

        video_data = video_path.read_bytes()
        b64 = base64.b64encode(video_data).decode()
        suffix = video_path.suffix.lower().lstrip(".")
        mime = {
            "mp4": "video/mp4", "mov": "video/quicktime",
            "avi": "video/x-msvideo", "wmv": "video/x-ms-wmv",
        }.get(suffix, "video/mp4")

        content = [
            {
                "type": "video_url",
                "video_url": {"url": f"data:{mime};base64,{b64}"},
                "fps": 2,
                "media_resolution": "default",
            },
            {"type": "text", "text": prompt},
        ]

        model = settings.openai_vision_model or settings.openai_model
        logger.info("Native video summarizing with OpenAI (%s, video=%s)", model, video_path.name)
        summary = self._chat_multimodal(content, max_tokens=4096)
        logger.info("Native video summary done: %d chars", len(summary))
        return summary

    def _summarize_with_frames(self, transcript: str, video_path: Path, lang: str, content_type: str | None) -> str:
        prompt = get_summary_prompt(content_type or "general", lang, multimodal=True).format(transcript=transcript)

        frames = _extract_frames(
            video_path,
            max_frames=settings.max_frames,
            interval=settings.frame_interval,
        )
        if not frames:
            raise RuntimeError("No frames extracted")

        content: list[dict] = []
        for frame in frames:
            b64 = base64.b64encode(frame.read_bytes()).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        content.append({"type": "text", "text": prompt})

        logger.info("Frame-based summarizing with OpenAI (%d frames, type=%s)", len(frames), content_type)
        summary = self._chat_multimodal(content, max_tokens=4096)
        logger.info("Frame-based summary done: %d chars", len(summary))
        return summary
