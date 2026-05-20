import logging
import os
import threading
from pathlib import Path

from core.config import settings

# Set HuggingFace mirror endpoint if configured
if settings.hf_endpoint:
    os.environ["HF_ENDPOINT"] = settings.hf_endpoint

logger = logging.getLogger(__name__)

_backend = None  # "faster" or "openai"
_model = None
_device = None
_lock = threading.Lock()


def _get_device() -> str:
    global _device
    if _device is not None:
        return _device

    try:
        import torch
        if torch.cuda.is_available():
            try:
                torch.zeros(1, device="cuda")
                _device = "cuda"
                logger.info("Whisper: using CUDA GPU")
            except Exception as e:
                _device = "cpu"
                logger.warning("Whisper: CUDA available but failed (%s), falling back to CPU", e)
        else:
            _device = "cpu"
            logger.info("Whisper: using CPU (CUDA not available)")
    except ImportError:
        _device = "cpu"
        logger.info("Whisper: using CPU (torch not available)")
    return _device


def _detect_backend() -> str:
    """Detect which Whisper backend to use. Prefer faster-whisper."""
    global _backend
    if _backend is not None:
        return _backend

    # Check config override first
    preferred = getattr(settings, "whisper_backend", "faster")

    if preferred == "faster":
        try:
            import faster_whisper  # noqa: F401
            _backend = "faster"
            logger.info("Using faster-whisper backend")
            return _backend
        except ImportError:
            logger.warning("faster-whisper not installed, falling back to openai-whisper")

    try:
        import whisper  # noqa: F401
        _backend = "openai"
        logger.info("Using openai-whisper backend")
    except ImportError:
        _backend = "faster"
        logger.info("Using faster-whisper backend (openai-whisper not available)")

    return _backend


def _get_model():
    global _model
    if _model is not None:
        return _model

    backend = _detect_backend()
    device = _get_device()

    if backend == "faster":
        from faster_whisper import WhisperModel
        compute_type = "float32" if device == "cuda" else "int8"
        logger.info("Loading faster-whisper model: %s on %s (compute=%s)", settings.whisper_model, device, compute_type)
        _model = WhisperModel(settings.whisper_model, device=device, compute_type=compute_type)
    else:
        import whisper
        logger.info("Loading openai-whisper model: %s on %s", settings.whisper_model, device)
        _model = whisper.load_model(settings.whisper_model, device=device)

    logger.info("Whisper model loaded")
    return _model


def _transcribe_once(model, backend: str, audio_path: Path, language: str) -> str:
    """Single transcription attempt."""
    if backend == "faster":
        segments, info = model.transcribe(str(audio_path), language=language, beam_size=5)
        text = " ".join(segment.text for segment in segments).strip()
        logger.info("Transcription done: %d chars (language: %.2f confidence)", len(text), info.language_probability)
    else:
        result = model.transcribe(str(audio_path), language=language, fp16=False)
        text = result.get("text", "").strip()
        logger.info("Transcription done: %d chars", len(text))
    return text


def transcribe(audio_path: Path, language: str = "zh") -> str:
    """Transcribe audio file to text using Whisper. Falls back to CPU on CUDA OOM."""
    global _device, _model

    logger.info("Transcribing: %s (lang=%s)", audio_path.name, language)

    with _lock:
        model = _get_model()
        backend = _detect_backend()

    try:
        return _transcribe_once(model, backend, audio_path, language)
    except RuntimeError as e:
        if "out of memory" in str(e).lower() and _device == "cuda":
            with _lock:
                logger.warning("CUDA OOM during transcription, falling back to CPU permanently")
                _device = "cpu"
                _model = None
                model = _get_model()
            return _transcribe_once(model, backend, audio_path, language)
        raise
