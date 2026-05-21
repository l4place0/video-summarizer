## Why

当前架构存在 5 个问题，其中 2 个是并发安全的红色风险：

1. **SQLite 无锁并发** — `Storage` 每次 `run_pipeline` 新建实例，多 pipeline 线程并发写入时无同步保护，WAL 模式下虽不崩溃但可能读到中间态
2. **`_stream_buffers` 无同步** — 模块级可变 dict 被 pipeline 线程写、SSE handler 读，存在 TOCTOU 竞态和迭代中 pop 的风险
3. **Frame extraction 层级违规** — `_extract_frames` 是纯 ffmpeg 操作却住在 `llm/openai_proto.py`，Claude 实现依赖 OpenAI 模块内部函数
4. **`vision/frames.py` 死代码** — 功能更全的帧提取模块从未被导入，`openai_proto.py` 重新实现了类似功能
5. **`requirements.txt` 与 `pyproject.toml` 不同步** — 前者列 `openai-whisper`，实际用 `faster-whisper`

## What Changes

### 并发安全（红色项）
- `Storage` 改为全局单例，所有调用方共享同一个连接 + `threading.Lock`
- `_stream_buffers` 改用 `threading.Lock` 保护，或替换为 `queue.Queue`

### 模块职责（黄色项）
- 将 `_extract_frames` / `_extract_frames_fps` 从 `llm/openai_proto.py` 移到 `vision/frames.py`
- `vision/frames.py` 合并两套实现（保留 timestamp seeking + fps fallback + scene detection）
- 所有调用方（pipeline、openai_proto、claude）改为从 `vision.frames` 导入
- 删除 `llm/openai_proto.py` 中的帧提取代码

### 依赖清理（绿色项）
- 删除 `requirements.txt`，统一用 `pyproject.toml` 管理依赖

## Capabilities

### Modified Capabilities
- `storage-singleton`: Storage 全局单例 + 线程安全锁
- `stream-buffer-sync`: stream_buffers 线程安全
- `vision-module-consolidation`: 帧提取统一到 vision 模块

## Impact

### 后端
- `core/storage/db.py` — 加锁 + 单例模式
- `core/pipeline.py` — stream_buffers 加锁，Storage 用单例，导入路径改为 vision
- `core/llm/openai_proto.py` — 删除 `_extract_frames` / `_extract_frames_fps`，导入改为 vision
- `core/llm/claude.py` — 导入改为 vision
- `core/vision/frames.py` — 合并 timestamp seeking + fps fallback + scene detection
- `core/api/routes.py` — Storage 用单例
- `core/main.py` — Storage 用单例
- 删除 `requirements.txt`

### 测试
- 现有测试不需要改动（功能不变，只是内部重组）
- 可选：为 Storage 单例和 stream_buffers 锁加并发测试
