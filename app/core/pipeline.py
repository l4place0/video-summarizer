import logging
from datetime import datetime, timezone
from pathlib import Path

from app.asr.whisper import transcribe
from app.core.config import settings
from app.llm import get_llm
from app.platforms.base import BasePlatform
from app.platforms.bilibili import BilibiliPlatform
from app.storage.db import Storage

logger = logging.getLogger(__name__)

PLATFORMS: list[BasePlatform] = [
    BilibiliPlatform(),
]


def get_platform(url: str) -> BasePlatform:
    for p in PLATFORMS:
        if p.match(url):
            return p
    raise ValueError(f"Unsupported URL: no platform matched for {url}")


def run_pipeline(task_id: str, url: str, language: str, llm_provider: str, detail: str) -> None:
    """Run the full pipeline for a task. Called in background."""
    db = Storage()
    try:
        # Resolve platform
        platform = get_platform(url)
        platform_name = platform.__class__.__name__.replace("Platform", "").lower()

        # Download
        db.update_task(task_id, status="downloading")
        logger.info("[%s] Downloading...", task_id[:8])
        audio_dir = settings.audio_dir / task_id
        audio_path, metadata = platform.download(url, audio_dir)
        db.update_task(task_id, platform=platform_name, metadata=metadata)

        # Transcribe
        db.update_task(task_id, status="transcribing")
        logger.info("[%s] Transcribing...", task_id[:8])
        transcript = transcribe(audio_path, language=language)

        # Save transcript
        transcript_path = settings.transcript_dir / f"{task_id}.txt"
        transcript_path.write_text(transcript, encoding="utf-8")
        db.update_task(task_id, transcript=transcript)

        # Summarize
        db.update_task(task_id, status="summarizing")
        logger.info("[%s] Summarizing...", task_id[:8])
        llm = get_llm(llm_provider)
        summary = llm.summarize(transcript, lang=language, detail=detail)

        # Done
        now = datetime.now(timezone.utc).isoformat()
        db.update_task(task_id, status="done", summary=summary, completed_at=now)
        logger.info("[%s] Done!", task_id[:8])

    except Exception as e:
        logger.error("[%s] Failed: %s", task_id[:8], e)
        now = datetime.now(timezone.utc).isoformat()
        db.update_task(task_id, status="failed", error=str(e), completed_at=now)
