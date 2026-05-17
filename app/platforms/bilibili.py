import re
import logging
from pathlib import Path

import yt_dlp

from app.platforms.base import BasePlatform

logger = logging.getLogger(__name__)

_BILIBILI_PATTERN = re.compile(r"bilibili\.com/video/(BV[\w]+)")


class BilibiliPlatform(BasePlatform):
    def match(self, url: str) -> bool:
        return bool(_BILIBILI_PATTERN.search(url))

    def parse_url(self, url: str) -> str:
        m = _BILIBILI_PATTERN.search(url)
        if not m:
            raise ValueError(f"Invalid Bilibili URL: {url}")
        return m.group(1)

    def download(self, url: str, output_dir: Path) -> tuple[Path, dict]:
        video_id = self.parse_url(url)
        output_dir.mkdir(parents=True, exist_ok=True)

        video_path = output_dir / f"{video_id}.mp4"
        audio_path = output_dir / f"{video_id}.wav"

        from app.core.config import settings

        ydl_opts = {
            "outtmpl": str(video_path),
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
        }

        if settings.cookies_path.is_file():
            ydl_opts["cookiefile"] = str(settings.cookies_path)

        logger.info("Downloading video: %s", video_id)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # yt-dlp may change the extension
            downloaded = Path(ydl.prepare_filename(info))
            if not downloaded.exists():
                # Try finding the file
                candidates = list(output_dir.glob(f"{video_id}.*"))
                if candidates:
                    downloaded = candidates[0]
                else:
                    raise FileNotFoundError(f"Downloaded file not found for {video_id}")
            video_path = downloaded

        metadata = {
            "title": info.get("title", ""),
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
            "uploader": info.get("uploader", ""),
            "video_id": video_id,
        }

        logger.info("Extracting audio: %s", video_id)
        self.extract_audio(video_path, audio_path)

        # Remove video file, keep only audio
        if video_path != audio_path and video_path.exists():
            video_path.unlink()

        return audio_path, metadata
