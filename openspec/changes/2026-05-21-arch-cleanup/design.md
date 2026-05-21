## Context

项目当前有 3 个 `Storage()` 实例（routes.py 全局、pipeline.py 每次新建、main.py lifespan），各自持有独立的 sqlite3 连接。`_stream_buffers` 是无保护的模块级 dict。帧提取逻辑重复分布在 `llm/openai_proto.py` 和 `vision/frames.py`。

## Goals / Non-goals

**Goals:**
- 消除并发写入风险
- 消除 stream_buffers 竞态
- 帧提取代码归到正确位置
- 删除死代码和过时依赖文件

**Non-goals:**
- 不改 SQLite 为其他数据库
- 不改 pipeline 的线程模型（threading.Thread 保持不变）
- 不改 API 接口或功能行为

## Decisions

### 1. Storage 单例 + 锁

用模块级单例 + `threading.Lock` 保护写操作：

```python
_lock = threading.Lock()
_instance: Storage | None = None

def get_storage() -> Storage:
    global _instance
    if _instance is None:
        _lock.acquire()
        if _instance is None:  # double-check
            _instance = Storage()
        _lock.release()
    return _instance
```

所有写操作加锁：
```python
def update_task(self, task_id: str, **kwargs):
    with _lock:
        # ... execute ...
        self._conn.commit()
```

读操作（`get_task`, `list_tasks`）不需要锁 — SQLite WAL 模式下并发读是安全的。

路由模块的 `db = Storage()` 改为 `db = get_storage()`，pipeline 中的 `db = Storage()` 也改为 `db = get_storage()`。

### 2. stream_buffers 用 Lock 保护

```python
_stream_lock = threading.Lock()
_stream_buffers: dict[str, list[str]] = {}

def _stream_callback(task_id: str, chunk: str):
    with _stream_lock:
        _stream_buffers.setdefault(task_id, []).append(chunk)

def get_stream_chunks(task_id: str) -> list[str]:
    with _stream_lock:
        return list(_stream_buffers.get(task_id, []))  # 返回副本

def _cleanup_stream(task_id: str):
    with _stream_lock:
        _stream_buffers.pop(task_id, None)
```

返回副本而非引用，避免 SSE handler 迭代时被 pipeline 线程修改。

### 3. 帧提取统一到 vision/frames.py

将 `openai_proto._extract_frames` 的 timestamp seeking 逻辑合并到 `vision/frames.py`，保留已有的 scene detection 模式。合并后的接口：

```python
def extract_frames(
    video_path: Path,
    output_dir: Path | None = None,
    max_frames: int = 20,
    mode: str = "timestamp",   # "timestamp" | "fps" | "scene"
    interval: int = 30,
    scene_threshold: float = 0.3,
) -> list[Path]:
```

三种模式：
- `timestamp`: 均匀时间戳 seeking（原 `_extract_frames` 的主逻辑）
- `fps`: fps filter fallback（原 `_extract_frames_fps`）
- `scene`: 场景切换检测（原 `vision/frames.py` 的 scene 模式）

`_get_video_duration` 辅助函数也一起移过来。

所有调用方改为：
```python
from core.vision.frames import extract_frames
```

### 4. 删除 requirements.txt

项目已全面使用 `pyproject.toml` + `uv`。`requirements.txt` 列的是过时的 `openai-whisper`，直接删除。

## Risks / Trade-offs

- **[Storage 单例]** 全局状态使测试更难隔离 → 可通过构造时传入 `db_path` 参数缓解，测试用独立 db 文件
- **[Lock 开销]** 写操作加锁增加微小延迟 → 可接受，写入频率很低（每 pipeline 一次 status update）
- **[帧提取重构]** 接口变化影响 3 个调用方 → 纯内部重组，无外部 API 变化
