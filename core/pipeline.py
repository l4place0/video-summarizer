import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from core.asr.whisper import transcribe
from core.config import settings
from core.llm import get_llm
from core.llm.openai_proto import _extract_frames
from core.platforms.base import BasePlatform
from core.platforms.bilibili import BilibiliPlatform
from core.platforms.youtube import YouTubePlatform
from core.storage.db import Storage

logger = logging.getLogger(__name__)

# Streaming buffers: task_id -> list of text chunks
_stream_buffers: dict[str, list[str]] = {}


def get_stream_chunks(task_id: str) -> list[str]:
    """Return accumulated chunks for a task (used by SSE endpoint)."""
    return _stream_buffers.get(task_id, [])


def _stream_callback(task_id: str, chunk: str):
    """Called by LLM for each streaming chunk."""
    if task_id not in _stream_buffers:
        _stream_buffers[task_id] = []
    _stream_buffers[task_id].append(chunk)


def _cleanup_stream(task_id: str):
    """Remove stream buffer after task completes."""
    _stream_buffers.pop(task_id, None)


def _build_metadata_context(metadata: dict, lang: str = "zh") -> str:
    """Build a supplementary context string from video metadata for LLM prompts."""
    parts = []
    desc = metadata.get("description", "").strip()
    if desc:
        label = "视频简介" if lang == "zh" else "Video Description"
        parts.append(f"[{label}]\n{desc}")
    tags = metadata.get("tags", [])
    if tags:
        label = "标签" if lang == "zh" else "Tags"
        parts.append(f"[{label}]\n{', '.join(tags)}")
    return "\n\n".join(parts)


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
        db.update_task(task_id, status="downloading", progress=10)
        cached = _try_cache(db, url, task_id)

        prefetched_frames: list[Path] | None = None

        if cached:
            transcript, metadata = cached
            db.update_task(task_id, platform=platform_name, metadata=metadata, transcript=transcript)
            logger.info("[%s] Using cached transcript (%d chars)", task_id[:8], len(transcript))
        else:
            logger.info("[%s] Downloading...", task_id[:8])
            audio_dir = settings.audio_dir / task_id
            keep_video = mode == "multimodal"
            audio_path, metadata, video_path = platform.download(url, audio_dir, keep_video=keep_video)
            db.update_task(task_id, platform=platform_name, metadata=metadata, progress=25)

            db.update_task(task_id, status="transcribing", progress=30)
            logger.info("[%s] Transcribing...", task_id[:8])

            # In multimodal mode, run frame extraction in parallel with transcription
            if mode == "multimodal" and video_path and video_path.exists():
                db.update_task(task_id, status="extracting_frames", progress=50)
                frames_output_dir = settings.frames_dir / task_id
                with ThreadPoolExecutor(max_workers=2) as pool:
                    transcribe_future = pool.submit(transcribe, audio_path, language)
                    frames_future = pool.submit(
                        _extract_frames, video_path, settings.max_frames, settings.frame_interval, frames_output_dir
                    )
                    transcript = transcribe_future.result()
                    prefetched_frames = frames_future.result()
                    logger.info("[%s] Parallel: transcription done (%d chars), frames extracted (%d)",
                                task_id[:8], len(transcript), len(prefetched_frames))
            else:
                transcript = transcribe(audio_path, language=language)

            transcript_path = settings.transcript_dir / f"{task_id}.txt"
            transcript_path.write_text(transcript, encoding="utf-8")
            db.update_task(task_id, transcript=transcript)

        llm = get_llm(llm_provider)
        is_multimodal = mode == "multimodal" and video_path and video_path.exists()

        # Build enriched transcript with metadata context (description, tags)
        meta_ctx = _build_metadata_context(metadata, language)
        enriched_transcript = f"{meta_ctx}\n\n[转录文本]\n{transcript}" if meta_ctx else transcript

        # Stage 1: Classify
        db.update_task(task_id, status="classifying", progress=75)
        logger.info("[%s] Classifying content...", task_id[:8])
        classification = llm.classify(enriched_transcript, lang=language, multimodal=is_multimodal)
        content_type = classification["type"]
        logger.info("[%s] Content type: %s", task_id[:8], content_type)

        # Persist classification results to metadata
        metadata["content_type"] = content_type
        metadata["language"] = language
        db.update_task(task_id, metadata=metadata)

        # Stage 2: Summarize with specialized prompt
        if is_multimodal:
            db.update_task(task_id, status="summarizing", progress=90)
            try:
                logger.info("[%s] Summarizing (multimodal, type=%s, prefetched_frames=%d)...",
                            task_id[:8], content_type, len(prefetched_frames) if prefetched_frames else 0)
                summary = llm.summarize_multimodal(
                    enriched_transcript, video_path, lang=language, detail=detail,
                    content_type=content_type, prefetched_frames=prefetched_frames,
                )
            except Exception as e:
                logger.warning("[%s] Multimodal failed (%s), falling back to text-only", task_id[:8], e)
                summary = llm.summarize(enriched_transcript, lang=language, detail=detail, content_type=content_type)
        else:
            db.update_task(task_id, status="summarizing", progress=90)
            logger.info("[%s] Summarizing (type=%s)...", task_id[:8], content_type)
            # Use streaming for text-only summarize
            chunks = []
            for chunk in llm.summarize_stream(enriched_transcript, lang=language, detail=detail, content_type=content_type):
                chunks.append(chunk)
                _stream_callback(task_id, chunk)
            summary = "".join(chunks)

        now = datetime.now(timezone.utc).isoformat()
        db.update_task(task_id, status="done", summary=summary, completed_at=now, progress=100)
        logger.info("[%s] Done!", task_id[:8])

    except Exception as e:
        logger.exception("[%s] Failed: %s", task_id[:8], e)
        now = datetime.now(timezone.utc).isoformat()
        db.update_task(task_id, status="failed", error=str(e), completed_at=now)
    finally:
        _cleanup_stream(task_id)
        if video_path and video_path.exists():
            video_path.unlink(missing_ok=True)
