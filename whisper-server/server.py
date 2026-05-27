"""Self-hosted Whisper ASR HTTP service.

Run with: uvicorn server:app --host 0.0.0.0 --port 8001
Requires: faster-whisper, fastapi, uvicorn, python-multipart
"""

import logging
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Whisper ASR Server")

# Model loaded at startup
_model = None
_model_name = os.environ.get("WHISPER_MODEL", "medium")
_device = os.environ.get("WHISPER_DEVICE", "cuda")
_compute_type = os.environ.get("WHISPER_COMPUTE_TYPE", "float32" if _device == "cuda" else "int8")


@app.on_event("startup")
def load_model():
    global _model
    from faster_whisper import WhisperModel
    logger.info("Loading Whisper model: %s on %s (compute=%s)", _model_name, _device, _compute_type)
    _model = WhisperModel(_model_name, device=_device, compute_type=_compute_type)
    logger.info("Model loaded")


def _format_timestamp(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"[{m:02d}:{s:02d}]"


@app.get("/health")
async def health():
    return {"status": "ok", "model": _model_name, "device": _device}


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = Form("zh")):
    """Transcribe uploaded audio file. Returns text with [MM:SS] timestamps."""
    if _model is None:
        return JSONResponse(status_code=503, content={"error": "Model not loaded"})

    # Save uploaded file to temp
    suffix = Path(audio.filename or "audio.wav").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        logger.info("Transcribing: %s (lang=%s)", audio.filename, language)
        segments, info = _model.transcribe(tmp_path, language=language, beam_size=5)

        lines = []
        for seg in segments:
            ts = _format_timestamp(seg.start)
            lines.append(f"{ts} {seg.text.strip()}")

        transcript = "\n".join(lines).strip()
        logger.info("Transcription done: %d chars, %d segments", len(transcript), len(lines))

        return {
            "transcript": transcript,
            "language": info.language,
            "language_probability": round(info.language_probability, 3),
            "segments": len(lines),
        }
    except Exception as e:
        logger.error("Transcription failed: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        os.unlink(tmp_path)
