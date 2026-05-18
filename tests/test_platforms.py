from core.platforms.bilibili import BilibiliPlatform
from core.platforms.youtube import YouTubePlatform


def test_bilibili_match():
    p = BilibiliPlatform()
    assert p.match("https://www.bilibili.com/video/BV1xx411c7XW")
    assert p.match("https://bilibili.com/video/BV1abc123")
    assert not p.match("https://youtube.com/watch?v=abc")


def test_bilibili_parse_url():
    p = BilibiliPlatform()
    assert p.parse_url("https://www.bilibili.com/video/BV1xx411c7XW") == "BV1xx411c7XW"


def test_bilibili_parse_invalid():
    p = BilibiliPlatform()
    try:
        p.parse_url("https://youtube.com/watch?v=abc")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_youtube_match():
    p = YouTubePlatform()
    assert p.match("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert p.match("https://youtube.com/watch?v=dQw4w9WgXcQ")
    assert p.match("https://youtu.be/dQw4w9WgXcQ")
    assert p.match("https://www.youtube.com/embed/dQw4w9WgXcQ")
    assert not p.match("https://bilibili.com/video/BV1xx411c7XW")
    assert not p.match("https://example.com")


def test_youtube_parse_url():
    p = YouTubePlatform()
    assert p.parse_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert p.parse_url("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert p.parse_url("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_youtube_parse_invalid():
    p = YouTubePlatform()
    try:
        p.parse_url("https://example.com")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
