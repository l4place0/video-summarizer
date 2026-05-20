import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)


def cache_size() -> int:
    total = 0
    if settings.cache_dir.exists():
        for f in settings.cache_dir.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total


def clean_cache(older_than_days: int | None = None, exclude_tasks: set[str] | None = None) -> tuple[int, int]:
    """Delete cached files. Returns (deleted_files, freed_bytes)."""
    if not settings.cache_dir.exists():
        return 0, 0

    excluded = exclude_tasks or set()
    deleted = 0
    freed = 0
    cutoff = None
    if older_than_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

    for f in settings.cache_dir.rglob("*"):
        if not f.is_file():
            continue
        if _should_exclude(f, excluded):
            continue
        if cutoff:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime >= cutoff:
                continue
        freed += f.stat().st_size
        f.unlink()
        deleted += 1

    # Remove empty dirs
    for d in sorted(settings.cache_dir.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()

    return deleted, freed


def clean_all() -> tuple[int, int]:
    """Delete entire cache directory. Returns (deleted_files, freed_bytes)."""
    deleted, freed = clean_cache()
    return deleted, freed


def _should_exclude(path: Path, exclude_tasks: set[str]) -> bool:
    """Check if a file belongs to an excluded task."""
    if not exclude_tasks:
        return False
    # Check if any part of the path matches a task_id
    for part in path.parts:
        if part in exclude_tasks:
            return True
    return False


def _clean_dir_by_age(directory: Path, max_age_days: int, exclude_tasks: set[str] | None = None) -> tuple[int, int]:
    """Delete files in directory older than max_age_days. Returns (deleted_files, freed_bytes)."""
    if not directory.exists():
        return 0, 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    excluded = exclude_tasks or set()
    deleted = 0
    freed = 0
    for f in directory.rglob("*"):
        if not f.is_file():
            continue
        if _should_exclude(f, excluded):
            continue
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        if mtime >= cutoff:
            continue
        freed += f.stat().st_size
        f.unlink()
        deleted += 1
    # Remove empty dirs
    for d in sorted(directory.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    return deleted, freed


def auto_clean_cache(video_days: int = 1, data_days: int = 7, exclude_tasks: set[str] | None = None) -> tuple[int, int]:
    """Auto-clean cache with different retention periods.

    - video_days: retention for video/audio files (audio_dir)
    - data_days: retention for transcripts, frames, and other data
    - exclude_tasks: set of task IDs whose files should be preserved

    Returns (total_deleted, total_freed_bytes).
    """
    total_deleted = 0
    total_freed = 0

    # Video/audio: short retention (1 day)
    d, f = _clean_dir_by_age(settings.audio_dir, video_days, exclude_tasks)
    if d:
        logger.info("Cache cleanup (audio/video, >%dd): deleted %d files, freed %d bytes", video_days, d, f)
    total_deleted += d
    total_freed += f

    # Transcripts: longer retention (7 days)
    d, f = _clean_dir_by_age(settings.transcript_dir, data_days, exclude_tasks)
    if d:
        logger.info("Cache cleanup (transcripts, >%dd): deleted %d files, freed %d bytes", data_days, d, f)
    total_deleted += d
    total_freed += f

    # Frames: longer retention (7 days)
    d, f = _clean_dir_by_age(settings.frames_dir, data_days, exclude_tasks)
    if d:
        logger.info("Cache cleanup (frames, >%dd): deleted %d files, freed %d bytes", data_days, d, f)
    total_deleted += d
    total_freed += f

    return total_deleted, total_freed
