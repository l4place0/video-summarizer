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


def _format_timestamp(seconds: float) -> str:
    """Format seconds as [MM:SS]."""
    m, s = divmod(int(seconds), 60)
    return f"[{m:02d}:{s:02d}]"


def _transcribe_once(model, backend: str, audio_path: Path, language: str, beam_size: int = 5) -> str:
    """Single transcription attempt. Returns text with segment timestamps."""
    if backend == "faster":
        segments, info = model.transcribe(str(audio_path), language=language, beam_size=beam_size)
        lines = []
        for seg in segments:
            ts = _format_timestamp(seg.start)
            lines.append(f"{ts} {seg.text.strip()}")
        text = "\n".join(lines).strip()
        logger.info("Transcription done: %d chars, %d segments (language: %.2f confidence, beam_size=%d)",
                    len(text), len(lines), info.language_probability, beam_size)
    else:
        result = model.transcribe(str(audio_path), language=language, fp16=False)
        raw_segments = result.get("segments", [])
        if raw_segments:
            lines = []
            for seg in raw_segments:
                ts = _format_timestamp(seg.get("start", 0))
                lines.append(f"{ts} {seg.get('text', '').strip()}")
            text = "\n".join(lines).strip()
        else:
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
        err_msg = str(e).lower()
        if "out of memory" in err_msg and _device == "cuda":
            with _lock:
                logger.warning("CUDA OOM during transcription, falling back to CPU permanently")
                _device = "cpu"
                _model = None
                model = _get_model()
            return _transcribe_once(model, backend, audio_path, language)
        # Long audio or CUDA memory issue: try openai-whisper on CPU
        if "reshape" in err_msg or "key.size" in err_msg or "out of memory" in err_msg:
            logger.warning("Whisper error (%s), trying openai-whisper CPU fallback", e)
            try:
                import whisper
                cpu_model = whisper.load_model(settings.whisper_model, device="cpu")
                result = cpu_model.transcribe(str(audio_path), language=language, fp16=False)
                raw_segments = result.get("segments", [])
                if raw_segments:
                    lines = []
                    for seg in raw_segments:
                        ts = _format_timestamp(seg.get("start", 0))
                        lines.append(f"{ts} {seg.get('text', '').strip()}")
                    return "\n".join(lines).strip()
                return result.get("text", "").strip()
            except Exception as fallback_e:
                logger.error("CPU fallback also failed: %s", fallback_e)
                raise e  # raise original error
        raise


class InProcessASR:
    """Wrapper around the in-process Whisper transcribe function (duck-typed BaseASR)."""

    def transcribe(self, audio_path: Path, language: str = "zh") -> str:
        return transcribe(audio_path, language)
