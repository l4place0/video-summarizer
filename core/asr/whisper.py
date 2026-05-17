import logging
from pathlib import Path

import torch
import whisper

from core.config import settings

logger = logging.getLogger(__name__)

_model = None
_device = None


def _get_device() -> str:
    global _device
    if _device is not None:
        return _device

    if torch.cuda.is_available():
        try:
            # Quick sanity check that CUDA actually works
            torch.zeros(1, device="cuda")
            _device = "cuda"
            logger.info("Whisper: using CUDA GPU")
        except Exception as e:
            _device = "cpu"
            logger.warning("Whisper: CUDA available but failed (%s), falling back to CPU", e)
    else:
        _device = "cpu"
        logger.info("Whisper: using CPU (CUDA not available)")
    return _device


def _get_model():
    global _model
    if _model is None:
        device = _get_device()
        logger.info("Loading Whisper model: %s on %s", settings.whisper_model, device)
        _model = whisper.load_model(settings.whisper_model, device=device)
        logger.info("Whisper model loaded")
    return _model


def transcribe(audio_path: Path, language: str = "zh") -> str:
    """Transcribe audio file to text using Whisper."""
    global _device, _model

    logger.info("Transcribing: %s (lang=%s)", audio_path.name, language)
    model = _get_model()
    device = _get_device()

    fp16 = device == "cuda"
    try:
        result = model.transcribe(str(audio_path), language=language, fp16=fp16)
    except (RuntimeError, ValueError) as e:
        if "nan" in str(e).lower() or "invalid values" in str(e).lower():
            logger.warning("FP16 failed on GPU, falling back to CPU for all subsequent transcriptions")
            _device = "cpu"
            _model = model.to("cpu")
            result = _model.transcribe(str(audio_path), language=language, fp16=False)
        else:
            raise

    text = result.get("text", "").strip()
    logger.info("Transcription done: %d chars", len(text))
    return text
