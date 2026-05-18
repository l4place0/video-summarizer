import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from core.asr.whisper import transcribe
from core.config import settings
from core.llm import get_llm
from core.platforms.base import BasePlatform
from core.platforms.bilibili import BilibiliPlatform
from core.platforms.youtube import YouTubePlatform
from core.storage.db import Storage

logger = logging.getLogger(__name__)

PLATFORMS: list[BasePlatform] = [
    BilibiliPlatform(),
    YouTubePlatform(),
]


def get_platform(url: str) -> BasePlatform:
    for p in PLATFORMS:
        if p.match(url):
            return p
    raise ValueError(f"Unsupported URL: no platform matched for {url}")


def _try_cache(db: Storage, url: str, task_id: str) -> tuple[str, dict] | None:
    """Try to find cached audio and transcript for the same video."""
    platform = get_platform(url)
    video_id = platform.parse_url(url)
    cached = db.find_cached_task(video_id)
    if not cached:
        return None

    cached_task_id = cached["task_id"]
    cached_audio = settings.audio_dir / cached_task_id / f"{video_id}.wav"
    cached_transcript = settings.transcript_dir / f"{cached_task_id}.txt"

    if not cached_audio.exists() or not cached_transcript.exists():
        return None

    new_audio_dir = settings.audio_dir / task_id
    new_audio_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cached_audio, new_audio_dir / f"{video_id}.wav")

    new_transcript = settings.transcript_dir / f"{task_id}.txt"
    shutil.copy2(cached_transcript, new_transcript)

    transcript = cached_transcript.read_text(encoding="utf-8")
    metadata = cached.get("metadata", {})
    logger.info("[%s] Cache hit for video_id=%s (from task %s)", task_id[:8], video_id, cached_task_id[:8])
    return transcript, metadata


def run_pipeline(task_id: str, url: str, language: str, llm_provider: str, detail: str, mode: str = "multimodal") -> None:
    """Run the full pipeline for a task. Called in background."""
    db = Storage()
    video_path: Path | None = None
    try:
        platform = get_platform(url)
        platform_name = platform.__class__.__name__.replace("Platform", "").lower()

        # Try cache first
        db.update_task(task_id, status="downloading")
        cached = _try_cache(db, url, task_id)

        if cached:
            transcript, metadata = cached
            db.update_task(task_id, platform=platform_name, metadata=metadata, transcript=transcript)
            logger.info("[%s] Using cached transcript (%d chars)", task_id[:8], len(transcript))
        else:
            logger.info("[%s] Downloading...", task_id[:8])
            audio_dir = settings.audio_dir / task_id
            keep_video = mode == "multimodal"
            audio_path, metadata, video_path = platform.download(url, audio_dir, keep_video=keep_video)
            db.update_task(task_id, platform=platform_name, metadata=metadata)

            db.update_task(task_id, status="transcribing")
            logger.info("[%s] Transcribing...", task_id[:8])
            transcript = transcribe(audio_path, language=language)

            transcript_path = settings.transcript_dir / f"{task_id}.txt"
            transcript_path.write_text(transcript, encoding="utf-8")
            db.update_task(task_id, transcript=transcript)

        llm = get_llm(llm_provider)
        is_multimodal = mode == "multimodal" and video_path and video_path.exists()

        # Stage 1: Classify
        db.update_task(task_id, status="classifying")
        logger.info("[%s] Classifying content...", task_id[:8])
        classification = llm.classify(transcript, lang=language, multimodal=is_multimodal)
        content_type = classification["type"]
        logger.info("[%s] Content type: %s", task_id[:8], content_type)

        # Stage 2: Summarize with specialized prompt
        if is_multimodal:
            db.update_task(task_id, status="summarizing")
            try:
                logger.info("[%s] Summarizing (multimodal, type=%s)...", task_id[:8], content_type)
                summary = llm.summarize_multimodal(transcript, video_path, lang=language, detail=detail, content_type=content_type)
            except Exception as e:
                logger.warning("[%s] Multimodal failed (%s), falling back to text-only", task_id[:8], e)
                summary = llm.summarize(transcript, lang=language, detail=detail, content_type=content_type)
        else:
            db.update_task(task_id, status="summarizing")
            logger.info("[%s] Summarizing (type=%s)...", task_id[:8], content_type)
            summary = llm.summarize(transcript, lang=language, detail=detail, content_type=content_type)

        now = datetime.now(timezone.utc).isoformat()
        db.update_task(task_id, status="done", summary=summary, completed_at=now)
        logger.info("[%s] Done!", task_id[:8])

    except Exception as e:
        logger.error("[%s] Failed: %s", task_id[:8], e)
        now = datetime.now(timezone.utc).isoformat()
        db.update_task(task_id, status="failed", error=str(e), completed_at=now)
    finally:
        if video_path and video_path.exists():
            video_path.unlink(missing_ok=True)
