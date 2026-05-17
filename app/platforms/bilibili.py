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

    def download(self, url: str, output_dir: Path, keep_video: bool = False) -> tuple[Path, dict, Path | None]:
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

        logger.info("Downloading audio: %s", video_id)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded = Path(ydl.prepare_filename(info))
            if not downloaded.exists():
                candidates = list(output_dir.glob(f"{video_id}.*"))
                if candidates:
                    downloaded = candidates[0]
                else:
                    raise FileNotFoundError(f"Downloaded file not found for {video_id}")
            audio_source = downloaded

        metadata = {
            "title": info.get("title", ""),
            "duration": info.get("duration", 0),
            "thumbnail": info.get("thumbnail", ""),
            "uploader": info.get("uploader", ""),
            "video_id": video_id,
        }

        logger.info("Extracting audio: %s", video_id)
        self.extract_audio(audio_source, audio_path)

        # Clean up audio source if different from final audio
        if audio_source != audio_path and audio_source.exists():
            audio_source.unlink()

        # For multimodal: download video stream separately for frame extraction
        ret_video = None
        if keep_video:
            video_only_path = output_dir / f"{video_id}_video.mp4"
            vid_opts = {
                "outtmpl": str(video_only_path),
                "format": "bestvideo[height<=720][ext=mp4]/bestvideo[height<=720]/bestvideo",
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
            }
            if settings.cookies_path.is_file():
                vid_opts["cookiefile"] = str(settings.cookies_path)

            logger.info("Downloading video stream: %s", video_id)
            try:
                with yt_dlp.YoutubeDL(vid_opts) as ydl:
                    vid_info = ydl.extract_info(url, download=True)
                    vid_file = Path(ydl.prepare_filename(vid_info))
                    if not vid_file.exists():
                        candidates = list(output_dir.glob(f"{video_id}_video.*"))
                        vid_file = candidates[0] if candidates else None
                    if vid_file and vid_file.exists():
                        ret_video = vid_file
                    else:
                        logger.warning("Video stream download failed, falling back to audio-only")
            except Exception as e:
                logger.warning("Video stream download failed: %s, falling back to audio-only", e)

        return audio_path, metadata, ret_video
