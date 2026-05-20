import re
import logging
from pathlib import Path

from core.platforms.base import YtdlpPlatform

logger = logging.getLogger(__name__)

_BILIBILI_PATTERN = re.compile(r"bilibili\.com/video/(BV[\w]+)")


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
