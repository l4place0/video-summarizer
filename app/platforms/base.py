from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BasePlatform(ABC):
    @abstractmethod
    def match(self, url: str) -> bool:
        """Return True if this platform handles the given URL."""
        ...

    @abstractmethod
    def parse_url(self, url: str) -> str:
        """Extract and return the video ID from the URL."""
        ...

    @abstractmethod
    def download(self, url: str, output_dir: Path, keep_video: bool = False) -> tuple[Path, dict, Path | None]:
        """Download video, extract audio. Return (audio_path, metadata, video_path).

        metadata should include: title, duration, thumbnail, etc.
        video_path is returned when keep_video=True, else None.
        """
        ...

    @staticmethod
    def check_ffmpeg() -> None:
        import shutil
        if not shutil.which("ffmpeg"):
            raise RuntimeError(
                "ffmpeg not found. Install it: apt install ffmpeg / brew install ffmpeg, "
                "or use Docker: docker compose up"
            )

    @staticmethod
    def extract_audio(video_path: Path, output_path: Path) -> Path:
        """Extract audio from video file using ffmpeg."""
        import subprocess

        BasePlatform.check_ffmpeg()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(video_path),
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )
        return output_path
