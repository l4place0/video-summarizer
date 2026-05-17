import logging
from pathlib import Path

import torch
import whisper

from core.config import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        logger.info("Loading Whisper model: %s", settings.whisper_model)
        _model = whisper.load_model(settings.whisper_model)
        logger.info("Whisper model loaded")
    return _model


def transcribe(audio_path: Path, language: str = "zh") -> str:
    """Transcribe audio file to text using Whisper."""
    logger.info("Transcribing: %s (lang=%s)", audio_path.name, language)
    model = _get_model()

    # Force FP32 on GPU to avoid NaN in logits (known Whisper issue)
    fp16 = torch.cuda.is_available()
    try:
        result = model.transcribe(str(audio_path), language=language, fp16=fp16)
    except (RuntimeError, ValueError) as e:
        if "nan" in str(e).lower() or "invalid values" in str(e).lower():
            logger.warning("FP16 failed, retrying with FP32")
            result = model.transcribe(str(audio_path), language=language, fp16=False)
        else:
            raise

    text = result.get("text", "").strip()
    logger.info("Transcription done: %d chars", len(text))
    return text
