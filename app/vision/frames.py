import logging
import subprocess
from pathlib import Path

from app.platforms.base import BasePlatform

logger = logging.getLogger(__name__)


def extract_frames(
    video_path: Path,
    output_dir: Path,
    max_frames: int = 10,
    mode: str = "interval",
    interval: int = 30,
    scene_threshold: float = 0.3,
) -> list[Path]:
    """Extract key frames from video using ffmpeg.

    Args:
        video_path: Path to the video file.
        output_dir: Directory to save frames.
        max_frames: Maximum number of frames to extract.
        mode: "interval" (fixed interval) or "scene" (scene change detection).
        interval: Seconds between frames (interval mode).
        scene_threshold: Scene change threshold 0-1 (scene mode).

    Returns:
        List of frame image paths, sorted by time.
    """
    BasePlatform.check_ffmpeg()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean previous frames
    for f in output_dir.glob("frame_*.jpg"):
        f.unlink()

    if mode == "scene":
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", f"select='gt(scene,{scene_threshold})',scale=1280:-2",
            "-vsync", "vfr", "-q:v", "3",
            "-frames:v", str(max_frames),
            str(output_dir / "frame_%04d.jpg"),
        ]
    else:
        # interval mode
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-vf", f"fps=1/{interval},scale=1280:-2",
            "-q:v", "3",
            "-frames:v", str(max_frames),
            str(output_dir / "frame_%04d.jpg"),
        ]

    logger.info("Extracting frames: mode=%s, max=%d", mode, max_frames)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("ffmpeg frame extraction failed: %s", result.stderr[-500:] if result.stderr else "")
        return []

    frames = sorted(output_dir.glob("frame_*.jpg"))
    logger.info("Extracted %d frames", len(frames))
    return frames
