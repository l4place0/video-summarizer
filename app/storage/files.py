import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import settings


def cache_size() -> int:
    total = 0
    if settings.cache_dir.exists():
        for f in settings.cache_dir.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total


def clean_cache(older_than_days: int | None = None) -> tuple[int, int]:
    """Delete cached files. Returns (deleted_files, freed_bytes)."""
    if not settings.cache_dir.exists():
        return 0, 0

    deleted = 0
    freed = 0
    cutoff = None
    if older_than_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

    for f in settings.cache_dir.rglob("*"):
        if not f.is_file():
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
