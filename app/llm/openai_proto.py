import logging

from openai import OpenAI

from app.core.config import settings
from app.llm.base import SUMMARY_PROMPTS, BaseLLM

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not configured")
        self.client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    def summarize(self, transcript: str, lang: str = "zh", detail: str = "normal") -> str:
        prompt_template = SUMMARY_PROMPTS.get(detail, SUMMARY_PROMPTS["normal"])
        prompt = prompt_template.get(lang, prompt_template["zh"]).format(transcript=transcript)

        logger.info("Summarizing with OpenAI (%s, %s)", settings.openai_model, detail)
        response = self.client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
        )
        summary = response.choices[0].message.content
        logger.info("Summary done: %d chars", len(summary))
        return summary
