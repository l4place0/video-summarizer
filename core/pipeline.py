import logging
import shutil
import time
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


class MetricsTracker:
    """Track resource usage metrics for pipeline stages."""

    def __init__(self):
        self.metrics: dict = {}
        self._stage_start: float = 0
        self._total_start: float = time.monotonic()

    def start_stage(self, stage: str):
        self._stage_start = time.monotonic()
        if stage not in self.metrics:
            self.metrics[stage] = {}

    def end_stage(self, stage: str, **extra):
        duration_ms = int((time.monotonic() - self._stage_start) * 1000)
        self.metrics[stage]["duration_ms"] = duration_ms
        for k, v in extra.items():
            self.metrics[stage][k] = v

    def finish(self) -> dict:
        self.metrics["total_duration_ms"] = int((time.monotonic() - self._total_start) * 1000)
        return self.metrics

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
    tracker = MetricsTracker()
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
            tracker.metrics["download"] = {"duration_ms": 0, "cached": True}
        else:
            logger.info("[%s] Downloading...", task_id[:8])
            tracker.start_stage("download")
            audio_dir = settings.audio_dir / task_id
            keep_video = mode == "multimodal"
            audio_path, metadata, video_path = platform.download(url, audio_dir, keep_video=keep_video)
            file_size = audio_path.stat().st_size if audio_path.exists() else 0
            tracker.end_stage("download", file_size_bytes=file_size, cached=False)
            db.update_task(task_id, platform=platform_name, metadata=metadata, progress=25)

            db.update_task(task_id, status="transcribing", progress=30)
            logger.info("[%s] Transcribing...", task_id[:8])

            # In multimodal mode, run frame extraction in parallel with transcription
            if mode == "multimodal" and video_path and video_path.exists():
                frames_output_dir = settings.frames_dir / task_id
                tracker.start_stage("transcribe")
                tracker.start_stage("extract_frames")

                # Heartbeat: update progress every 30s so the UI shows activity
                _stop_heartbeat = threading.Event()
                def _heartbeat():
                    pct = 30
                    while not _stop_heartbeat.wait(timeout=30):
                        pct = min(pct + 3, 58)
                        try:
                            db.update_task(task_id, progress=pct)
                        except Exception:
                            pass
                hb_thread = threading.Thread(target=_heartbeat, daemon=True)
                hb_thread.start()

                with ThreadPoolExecutor(max_workers=2) as pool:
                    transcribe_future = pool.submit(transcribe, audio_path, language)
                    frames_future = pool.submit(
                        _extract_frames, video_path, settings.max_frames, settings.frame_interval, frames_output_dir
                    )
                    transcript = transcribe_future.result()
                    prefetched_frames = frames_future.result()

                _stop_heartbeat.set()
                tracker.end_stage("transcribe", text_length=len(transcript))
                tracker.end_stage("extract_frames", frame_count=len(prefetched_frames))
                logger.info("[%s] Parallel: transcription done (%d chars), frames extracted (%d)",
                            task_id[:8], len(transcript), len(prefetched_frames))
            else:
                tracker.start_stage("transcribe")
                transcript = transcribe(audio_path, language=language)
                tracker.end_stage("transcribe", text_length=len(transcript))

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
        tracker.start_stage("classify")
        classification = llm.classify(enriched_transcript, lang=language, multimodal=is_multimodal)
        tracker.end_stage("classify", api_calls=1)
        content_type = classification["type"]
        logger.info("[%s] Content type: %s", task_id[:8], content_type)

        # Persist classification results to metadata
        metadata["content_type"] = content_type
        metadata["language"] = language
        db.update_task(task_id, metadata=metadata)

        # Stage 2: Summarize with specialized prompt
        if is_multimodal:
            db.update_task(task_id, status="summarizing", progress=90)
            tracker.start_stage("summarize")
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
            tracker.end_stage("summarize", api_calls=1)
        else:
            db.update_task(task_id, status="summarizing", progress=90)
            logger.info("[%s] Summarizing (type=%s)...", task_id[:8], content_type)
            # Use streaming for text-only summarize
            tracker.start_stage("summarize")
            chunks = []
            for chunk in llm.summarize_stream(enriched_transcript, lang=language, detail=detail, content_type=content_type):
                chunks.append(chunk)
                _stream_callback(task_id, chunk)
            summary = "".join(chunks)
            tracker.end_stage("summarize", api_calls=1)

        # Save metrics to metadata
        metadata["metrics"] = tracker.finish()
        now = datetime.now(timezone.utc).isoformat()
        db.update_task(task_id, status="done", summary=summary, completed_at=now, progress=100, metadata=metadata)
        logger.info("[%s] Done! Total: %dms", task_id[:8], metadata["metrics"]["total_duration_ms"])

    except Exception as e:
        logger.exception("[%s] Failed: %s", task_id[:8], e)
        now = datetime.now(timezone.utc).isoformat()
        # Save partial metrics even on failure
        try:
            metadata["metrics"] = tracker.finish()
            db.update_task(task_id, status="failed", error=str(e), completed_at=now, metadata=metadata)
        except Exception:
            db.update_task(task_id, status="failed", error=str(e), completed_at=now)
    finally:
        _cleanup_stream(task_id)
        if video_path and video_path.exists():
            video_path.unlink(missing_ok=True)
