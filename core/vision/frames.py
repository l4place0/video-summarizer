import logging
import subprocess
import tempfile
from pathlib import Path

from core.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


def _get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return float(result.stdout.strip())
    except Exception as e:
        logger.warning("ffprobe failed for %s: %s", video_path.name, e)
        return 0


def extract_frames(
    video_path: Path,
    output_dir: Path | None = None,
    max_frames: int = 20,
    mode: str = "timestamp",
    interval: int = 30,
    scene_threshold: float = 0.3,
) -> list[Path]:
    """Extract key frames from video using ffmpeg.

    Modes:
        timestamp: Seek to evenly-spaced timestamps (fast, default).
        fps: Decode with fps filter (fallback when duration unknown).
        scene: Scene change detection.
    """
    if mode == "scene":
        BasePlatform.check_ffmpeg()

    if output_dir:
        tmp_dir = output_dir
        tmp_dir.mkdir(parents=True, exist_ok=True)
    else:
        tmp_dir = Path(tempfile.mkdtemp(prefix="frames_"))

    if mode == "scene":
        return _extract_frames_scene(video_path, tmp_dir, max_frames, scene_threshold)
    if mode == "fps":
        return _extract_frames_fps(video_path, tmp_dir, max_frames, interval)
    return _extract_frames_timestamp(video_path, tmp_dir, max_frames, interval)


def _extract_frames_timestamp(video_path: Path, tmp_dir: Path, max_frames: int, interval: int) -> list[Path]:
    """Extract frames by seeking to evenly-spaced timestamps (fast for long videos)."""
    duration = _get_video_duration(video_path)
    if duration <= 0:
        logger.warning("Could not determine video duration, falling back to fps filter")
        return _extract_frames_fps(video_path, tmp_dir, max_frames, interval)

    step = max(interval, duration / max_frames)
    timestamps = []
    t = step / 2
    while t < duration and len(timestamps) < max_frames:
        timestamps.append(t)
        t += step

    logger.info("Extracting %d frames from %.0fs video (step=%.0fs)", len(timestamps), duration, step)

    frames = []
    for i, ts in enumerate(timestamps):
        out_path = tmp_dir / f"frame_{i+1:04d}.jpg"
        cmd = [
            "ffmpeg", "-ss", f"{ts:.1f}",
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",
            str(out_path),
            "-y", "-hide_banner", "-loglevel", "error",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and out_path.exists():
                frames.append(out_path)
            else:
                logger.warning("Failed to extract frame at %.1fs: %s", ts, result.stderr[:200])
        except subprocess.TimeoutExpired:
            logger.warning("Timeout extracting frame at %.1fs", ts)

    logger.info("Extracted %d/%d frames from %s", len(frames), len(timestamps), video_path.name)
    return frames


def _extract_frames_fps(video_path: Path, tmp_dir: Path, max_frames: int, interval: int) -> list[Path]:
    """Fallback: extract frames using fps filter (for unknown duration)."""
    fps_filter = f"fps=1/{interval}"
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", fps_filter,
        "-frames:v", str(max_frames),
        "-q:v", "2",
        str(tmp_dir / "frame_%04d.jpg"),
        "-y", "-hide_banner", "-loglevel", "error",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        logger.warning("ffmpeg frame extraction failed: %s", result.stderr)
        return []
    return sorted(tmp_dir.glob("frame_*.jpg"))


def _extract_frames_scene(video_path: Path, tmp_dir: Path, max_frames: int, threshold: float) -> list[Path]:
    """Extract frames at scene change boundaries."""
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", f"select='gt(scene,{threshold})',scale=1280:-2",
        "-vsync", "vfr", "-q:v", "3",
        "-frames:v", str(max_frames),
        str(tmp_dir / "frame_%04d.jpg"),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("ffmpeg frame extraction failed: %s", result.stderr[-500:] if result.stderr else "")
        return []
    frames = sorted(tmp_dir.glob("frame_*.jpg"))
    logger.info("Extracted %d frames (scene mode)", len(frames))
    return frames
