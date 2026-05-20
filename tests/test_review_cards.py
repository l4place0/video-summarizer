"""Tests for review card parsing."""

from core.review_doc import parse_review_cards


def test_parse_normal():
    summary = """## 核心内容
一些总结。

## 复习卡片

**Q1:** 什么是 SM-2 算法？
**A1:** 通过 ease factor 和间隔天数动态调整复习频率的算法。

**Q2:** 帧提取用什么工具？
**A2:** ffmpeg 的 timestamp seeking。

**Q3:** 第三个问题？
**A3:** 第三个答案。
"""
    cards = parse_review_cards(summary)
    assert len(cards) == 3
    assert cards[0]["question"] == "什么是 SM-2 算法？"
    assert cards[0]["answer"] == "通过 ease factor 和间隔天数动态调整复习频率的算法。"
    assert cards[2]["question"] == "第三个问题？"


def test_parse_no_section():
    summary = "## 核心内容\n没有卡片的总结。"
    assert parse_review_cards(summary) == []


def test_parse_english():
    summary = """## Core Content
Some summary.

## Review Cards

**Q1:** What is SM-2?
**A1:** An algorithm that adjusts review intervals.

**Q2:** What tool for frames?
**A2:** ffmpeg timestamp seeking.
"""
    cards = parse_review_cards(summary)
    assert len(cards) == 2
    assert cards[1]["answer"] == "ffmpeg timestamp seeking."


def test_parse_malformed():
    """Q/A count mismatch — should truncate to shortest."""
    summary = """## 复习卡片

**Q1:** 问题一？
**A1:** 答案一。

**Q2:** 问题二？
"""
    cards = parse_review_cards(summary)
    assert len(cards) == 1
    assert cards[0]["question"] == "问题一？"


def test_parse_empty_section():
    summary = "## 复习卡片\n\n没有内容。"
    assert parse_review_cards(summary) == []
