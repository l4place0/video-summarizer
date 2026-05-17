from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, HttpUrl


class TaskStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    DONE = "done"
    FAILED = "failed"


class SummarizeRequest(BaseModel):
    url: str
    language: str = "zh"
    llm_provider: str = "claude"
    detail: str = "normal"


class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TaskDetail(BaseModel):
    task_id: str
    url: str
    platform: str
    status: TaskStatus
    summary: Optional[str] = None
    transcript: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    metadata: Optional[dict] = None
    error: Optional[str] = None


class TaskListItem(BaseModel):
    task_id: str
    url: str
    platform: str
    status: TaskStatus
    summary: Optional[str] = None
    created_at: datetime
    metadata: Optional[dict] = None


class TaskListResponse(BaseModel):
    tasks: list[TaskListItem]


class StorageInfo(BaseModel):
    db_size_bytes: int
    cache_size_bytes: int
    task_count: int


class StorageCleanupResult(BaseModel):
    deleted_files: int
    deleted_tasks: int
    freed_bytes: int


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
