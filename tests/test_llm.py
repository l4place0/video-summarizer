from app.llm.base import SUMMARY_PROMPTS


def test_prompts_exist():
    assert "normal" in SUMMARY_PROMPTS
    assert "detailed" in SUMMARY_PROMPTS
    assert "zh" in SUMMARY_PROMPTS["normal"]
    assert "en" in SUMMARY_PROMPTS["normal"]


def test_prompt_format():
    template = SUMMARY_PROMPTS["normal"]["zh"]
    result = template.format(transcript="hello world")
    assert "hello world" in result
