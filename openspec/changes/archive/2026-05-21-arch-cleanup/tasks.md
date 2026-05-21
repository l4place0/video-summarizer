## 1. Storage 单例 + 写锁

- [x] 1.1 在 `core/storage/db.py` 中添加模块级 `_lock = threading.Lock()` 和 `_instance: Storage | None = None`
- [x] 1.2 实现 `get_storage() -> Storage` 单例工厂函数（double-check locking）
- [x] 1.3 给所有写操作（`create_task`, `update_task`, `delete_task`, `set_favorite`, `reset_task`, `delete_tasks`）加 `_lock` 保护
- [x] 1.4 读操作（`get_task`, `list_tasks`, `get_task_status`, `task_count`, `get_active_and_favorite_task_ids`）不加锁（WAL 并发读安全）
- [x] 1.5 修改 `core/api/routes.py`：`db = Storage()` → `db = get_storage()`
- [x] 1.6 修改 `core/pipeline.py`：`db = Storage()` → `db = get_storage()`
- [x] 1.7 修改 `core/main.py`：`storage = Storage()` → `storage = get_storage()`

## 2. stream_buffers 线程安全

- [x] 2.1 在 `core/pipeline.py` 中添加 `_stream_lock = threading.Lock()`
- [x] 2.2 `_stream_callback` 加锁保护 dict 写入
- [x] 2.3 `get_stream_chunks` 加锁并返回 list 副本（避免迭代中被修改）
- [x] 2.4 `_cleanup_stream` 加锁保护 pop 操作

## 3. 帧提取统一到 vision 模块

- [x] 3.1 将 `_get_video_duration` 从 `llm/openai_proto.py` 移到 `vision/frames.py`
- [x] 3.2 将 timestamp seeking 逻辑（原 `_extract_frames` 主逻辑）合并到 `vision/frames.py` 的 `extract_frames` 函数，作为 `mode="timestamp"`
- [x] 3.3 将 fps fallback 逻辑（原 `_extract_frames_fps`）合并到 `vision/frames.py`，作为 `mode="fps"`
- [x] 3.4 保留 `vision/frames.py` 已有的 scene detection 模式
- [x] 3.5 统一接口：`extract_frames(video_path, output_dir, max_frames, mode, interval, scene_threshold) -> list[Path]`
- [x] 3.6 修改 `core/pipeline.py`：`from core.llm.openai_proto import _extract_frames` → `from core.vision.frames import extract_frames`
- [x] 3.7 修改 `core/llm/openai_proto.py`：删除 `_extract_frames` 和 `_extract_frames_fps`，改为 `from core.vision.frames import extract_frames`
- [x] 3.8 修改 `core/llm/claude.py`：`from core.llm.openai_proto import _extract_frames` → `from core.vision.frames import extract_frames`
- [x] 3.9 删除 `llm/openai_proto.py` 中不再需要的 `import tempfile` 和帧提取相关代码

## 4. 依赖清理

- [x] 4.1 删除 `requirements.txt`

## 5. 验证

- [x] 5.1 运行 `uv run python -m pytest tests/ -v` 确认所有测试通过
- [x] 5.2 手动启动服务 `uv run uvicorn core.main:app`，提交一个任务验证完整 pipeline 流程正常
