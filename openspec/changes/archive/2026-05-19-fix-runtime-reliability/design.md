## Context

项目有三个已知运行时问题：

1. **Claude 帧提取**：`claude.py` 的 `_extract_frames()` 使用 `fps=1/{interval}` 滤镜，ffmpeg 会解码整个视频文件。对于长视频（>30min）这会消耗大量时间和内存，甚至挂起。而 `openai_proto.py` 已经实现了 timestamp seeking 方式（`-ss` 参数），快速且有超时保护。

2. **CUDA 回退**：`whisper.py` 的 `_get_device()` 在初始化时检测 CUDA，但 `_device` 全局缓存后不再更新。如果 CUDA 在模型加载或推理时 OOM，没有机制切换到 CPU，后续调用继续失败。

3. **分类结果丢失**：`pipeline.py` 在 classify 阶段获得 `content_type` 和 `language`，但只用于选择 prompt，没有写入数据库 metadata。导出 Markdown 时这两个字段为空。

## Goals / Non-Goals

**Goals:**
- Claude 帧提取使用 timestamp seeking，与 OpenAI LLM 行为一致
- 所有帧提取操作有超时保护（单帧 30s）
- CUDA OOM 后永久回退到 CPU，避免重复失败
- 分类结果（content_type、language）持久化到 metadata
- 导出 Markdown 自动填充 content_type/language

**Non-Goals:**
- 不做自动 GPU 显存检测/模型大小选择
- 不做帧提取的并行化优化
- 不修改数据库 schema（利用现有 metadata JSON 字段）

## Decisions

### 1. Claude 帧提取：复用 openai_proto 的 `_extract_frames`

将 `openai_proto.py` 中的 `_extract_frames()` 和 `_extract_frames_fps()` 移到共享模块（如 `core/vision/frames.py`），或直接在 `claude.py` 中导入使用。

**选择：直接导入 `core.llm.openai_proto._extract_frames`**

理由：
- 最小改动，不需要重构模块结构
- `openai_proto._extract_frames` 已有 timestamp seeking + 超时 + duration 检测 + fps fallback
- 未来如需共享可以再提取到独立模块

### 2. CUDA 回退：catch-and-cache 模式

在 `transcribe()` 中捕获 CUDA OOM 异常，设置 `_device = "cpu"` 并重新加载模型。

```
try:
    result = model.transcribe(...)
except RuntimeError as e:
    if "out of memory" in str(e) and _device == "cuda":
        _device = "cpu"
        _model = None  # force reload on CPU
        model = _get_model()
        result = model.transcribe(...)  # retry on CPU
```

**为什么不重新设计 _get_device()：** 问题不在检测阶段（CUDA available 检查通常成功），而在运行时 OOM。catch-and-cache 在失败点处理，比预防性检测更可靠。

### 3. 分类结果存储：扩展 metadata dict

在 `pipeline.py` classify 之后，将 `content_type` 和 `language` 写入 metadata：

```python
metadata["content_type"] = content_type
metadata["language"] = language
db.update_task(task_id, metadata=metadata)
```

理由：
- metadata 已经是 JSON dict，无需 schema 迁移
- 导出功能可以直接从 `task.metadata.content_type` 读取
- 保持 language 作为 pipeline 参数（用户选择），而非 LLM 推断

## Risks / Trade-offs

- [Claude 导入循环] `claude.py` 导入 `openai_proto._extract_frames` 可能产生循环依赖 → 实际不会，因为 `openai_proto` 不导入 `claude`
- [CUDA 回退后性能] CPU 推理显著慢于 GPU → 用户体验优于完全失败，可接受
- [metadata 覆盖] 重新 classify 时会覆盖之前的 content_type → 当前无此场景，pipeline 只运行一次
