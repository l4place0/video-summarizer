from app.platforms.bilibili import BilibiliPlatform


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
