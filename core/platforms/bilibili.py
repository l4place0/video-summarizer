import re
import logging
from pathlib import Path

import yt_dlp

from core.platforms.base import YtdlpPlatform

logger = logging.getLogger(__name__)

_BILIBILI_PATTERN = re.compile(r"bilibili\.com/video/(BV[\w]+)")
_TEST_VIDEO_ID = "BV1GJ411x7h7"  # Stable public test video


class BilibiliPlatform(YtdlpPlatform):
    def match(self, url: str) -> bool:
        return bool(_BILIBILI_PATTERN.search(url))

    def parse_url(self, url: str) -> str:
        m = _BILIBILI_PATTERN.search(url)
        if not m:
            raise ValueError(f"Invalid Bilibili URL: {url}")
        return m.group(1)

    def _get_ydl_opts(self, output_path: Path) -> dict:
        opts = super()._get_ydl_opts(output_path)
        from core.config import settings
        if settings.cookies_path.is_file():
            opts["cookiefile"] = str(settings.cookies_path)
        return opts

    @staticmethod
    def check_cookies(cookies_path: Path | None = None) -> str:
        """Check if Bilibili cookies are valid. Returns 'valid', 'expired', or 'not_configured'."""
        from core.config import settings
        path = cookies_path or settings.cookies_path
        if not path.is_file():
            return "not_configured"

        opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,
            "cookiefile": str(path),
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(f"https://www.bilibili.com/video/{_TEST_VIDEO_ID}", download=False)
                if info and info.get("title"):
                    return "valid"
                return "expired"
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                return "expired"
            logger.warning("Cookies check failed: %s", e)
            return "expired"
