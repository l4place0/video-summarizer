import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from core.llm.prompts import (
    CLASSIFY_PROMPT,
    CLASSIFY_PROMPT_MULTIMODAL,
    CONTENT_TYPES,
    SUMMARY_PROMPTS,
    get_classify_prompt,
    get_summary_prompt,
)

logger = logging.getLogger(__name__)


class BaseLLM(ABC):
    @abstractmethod
    def _chat(self, prompt: str, max_tokens: int = 4096) -> str:
        """Send a text-only prompt to the LLM and return the response text."""
        ...

    def _chat_multimodal(self, content: list[dict], max_tokens: int = 4096) -> str:
        """Send a multimodal content array to the LLM. Default: extract text parts only."""
        text_parts = [p["text"] for p in content if p.get("type") == "text"]
        return self._chat("\n".join(text_parts), max_tokens=max_tokens)

    def classify(self, transcript: str, lang: str = "zh", multimodal: bool = False) -> dict:
        """Stage 1: Quick classification. Returns {"summary": str, "type": str}."""
        prompt = get_classify_prompt(lang, multimodal).format(transcript=transcript[:3000])
        try:
            raw = self._chat(prompt, max_tokens=500)
            # Extract JSON from response (handle markdown code blocks)
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            result = json.loads(text)
            content_type = result.get("type", "general")
            if content_type not in CONTENT_TYPES:
                content_type = "general"
            return {"summary": result.get("summary", ""), "type": content_type}
        except Exception as e:
            logger.warning("Classification failed: %s, using general", e)
            return {"summary": "", "type": "general"}

    def summarize(self, transcript: str, lang: str = "zh", detail: str = "normal", content_type: str | None = None) -> str:
        """Stage 2: Summarize with structured prompt based on content type."""
        ct = content_type or "general"
        prompt = get_summary_prompt(ct, lang, multimodal=False).format(transcript=transcript)
        return self._chat(prompt, max_tokens=4096)

    def summarize_multimodal(
        self, transcript: str, video_path: Path, lang: str = "zh", detail: str = "normal", content_type: str | None = None
    ) -> str:
        """Stage 2: Summarize with video + structured prompt. Default: fall back to text-only."""
        return self.summarize(transcript, lang, detail, content_type=content_type)
