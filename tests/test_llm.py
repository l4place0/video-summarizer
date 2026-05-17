"""Tests for LLM prompt system."""
from core.llm.prompts import SUMMARY_PROMPTS, CONTENT_TYPES, get_summary_prompt, get_classify_prompt


def test_content_types():
    assert "tutorial" in CONTENT_TYPES
    assert "tech_talk" in CONTENT_TYPES
    assert "general" in CONTENT_TYPES


def test_summary_prompts_exist():
    for ct in CONTENT_TYPES:
        assert ct in SUMMARY_PROMPTS, f"Missing content type: {ct}"
        assert "zh" in SUMMARY_PROMPTS[ct]
        assert "en" in SUMMARY_PROMPTS[ct]


def test_prompt_format():
    for ct in CONTENT_TYPES:
        template = get_summary_prompt(ct, "zh")
        result = template.format(transcript="hello world")
        assert "hello world" in result


def test_classify_prompt():
    prompt = get_classify_prompt("zh")
    assert "{transcript}" in prompt
    prompt_en = get_classify_prompt("en")
    assert "{transcript}" in prompt_en


def test_multimodal_suffix():
    base = get_summary_prompt("general", "zh", multimodal=False)
    multi = get_summary_prompt("general", "zh", multimodal=True)
    assert len(multi) > len(base)
    assert "画面" in multi or "视觉" in multi
