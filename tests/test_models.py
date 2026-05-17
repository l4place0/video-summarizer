from core.models import (
    SummarizeRequest,
    TaskResponse,
    TaskStatus,
    HealthResponse,
    StorageInfo,
)


def test_summarize_request_defaults():
    req = SummarizeRequest(url="https://bilibili.com/video/BV123")
    assert req.language == "zh"
    assert req.llm_provider == "openai"
    assert req.detail == "normal"
    assert req.mode == "multimodal"


def test_task_status_values():
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.DONE == "done"
    assert TaskStatus.FAILED == "failed"


def test_health_response():
    h = HealthResponse()
    assert h.status == "ok"
    assert h.version == "0.1.0"


def test_storage_info():
    s = StorageInfo(db_size_bytes=100, cache_size_bytes=200, task_count=3)
    assert s.task_count == 3
