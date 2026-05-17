import logging
import threading

from fastapi import APIRouter, HTTPException, Query

from app.core.models import (
    HealthResponse,
    StorageCleanupResult,
    StorageInfo,
    SummarizeRequest,
    TaskDetail,
    TaskListItem,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
)
from app.core.pipeline import get_platform, run_pipeline
from app.storage.db import Storage
from app.storage.files import cache_size, clean_all, clean_cache

logger = logging.getLogger(__name__)
router = APIRouter()
db = Storage()


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@router.post("/api/summarize", response_model=TaskResponse, status_code=202)
async def summarize(req: SummarizeRequest):
    # Validate URL
    try:
        get_platform(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    task_id = db.create_task(req.url, platform="unknown")

    # Run pipeline in background thread
    thread = threading.Thread(
        target=run_pipeline,
        args=(task_id, req.url, req.language, req.llm_provider, req.detail),
        daemon=True,
    )
    thread.start()

    return TaskResponse(task_id=task_id, status=TaskStatus.PENDING)


@router.get("/api/tasks", response_model=TaskListResponse)
async def list_tasks():
    tasks = db.list_tasks()
    items = [
        TaskListItem(
            task_id=t["task_id"],
            url=t["url"],
            platform=t["platform"],
            status=t["status"],
            summary=t.get("summary"),
            created_at=t["created_at"],
            metadata=t.get("metadata"),
        )
        for t in tasks
    ]
    return TaskListResponse(tasks=items)


@router.get("/api/tasks/{task_id}", response_model=TaskDetail)
async def get_task(task_id: str):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskDetail(
        task_id=task["task_id"],
        url=task["url"],
        platform=task["platform"],
        status=task["status"],
        summary=task.get("summary"),
        transcript=task.get("transcript"),
        created_at=task["created_at"],
        completed_at=task.get("completed_at"),
        metadata=task.get("metadata"),
        error=task.get("error"),
    )


@router.get("/api/storage", response_model=StorageInfo)
async def get_storage():
    return StorageInfo(
        db_size_bytes=db.db_size(),
        cache_size_bytes=cache_size(),
        task_count=db.task_count(),
    )


@router.delete("/api/storage", response_model=StorageCleanupResult)
async def delete_storage(older_than: str | None = Query(None, description="e.g. '7d'")):
    days = None
    if older_than:
        try:
            days = int(older_than.rstrip("d"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid older_than format, use e.g. '7d'")

    deleted_files, freed = clean_cache(older_than_days=days)
    deleted_tasks = db.delete_tasks(older_than_days=days)

    return StorageCleanupResult(
        deleted_files=deleted_files,
        deleted_tasks=deleted_tasks,
        freed_bytes=freed,
    )
