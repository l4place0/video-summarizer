"""ASR provider that calls OpenAI's Whisper API (cloud)."""

import logging
from pathlib import Path

from openai import OpenAI

from core.asr.base import BaseASR

logger = logging.getLogger(__name__)


class OpenAIWhisperAPI(BaseASR):
    """Transcribe using OpenAI's Whisper API."""

    def __init__(self, api_key: str, model: str = "whisper-1", base_url: str = ""):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model

    def transcribe(self, audio_path: Path, language: str = "zh") -> str:
        logger.info("Calling OpenAI Whisper API for %s", audio_path.name)
        with open(audio_path, "rb") as f:
            resp = self.client.audio.transcriptions.create(
                model=self.model,
                file=f,
                language=language,
            )
        transcript = resp.text
        logger.info("OpenAI Whisper returned %d chars", len(transcript))
        return transcript
