import logging

import anthropic

from app.core.config import settings
from app.llm.base import SUMMARY_PROMPTS, BaseLLM

logger = logging.getLogger(__name__)


class ClaudeLLM(BaseLLM):
    def __init__(self):
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        kwargs = {"api_key": settings.anthropic_api_key}
        if settings.anthropic_base_url:
            kwargs["base_url"] = settings.anthropic_base_url
        self.client = anthropic.Anthropic(**kwargs)

    def summarize(self, transcript: str, lang: str = "zh", detail: str = "normal") -> str:
        prompt_template = SUMMARY_PROMPTS.get(detail, SUMMARY_PROMPTS["normal"])
        prompt = prompt_template.get(lang, prompt_template["zh"]).format(transcript=transcript)

        logger.info("Summarizing with Claude (%s, %s)", settings.claude_model, detail)
        message = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        summary = message.content[0].text
        logger.info("Summary done: %d chars", len(summary))
        return summary
