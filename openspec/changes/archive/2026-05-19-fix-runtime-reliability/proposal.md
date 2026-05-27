## Why

项目存在三个已知的运行时可靠性问题：Claude LLM 的帧提取在长视频上会挂起（使用 fps filter 解码整个文件）、CUDA OOM 后无法自动回退到 CPU（设备选择全局缓存后不更新）、分类结果（content_type/language）在 pipeline 结束后丢失未存入数据库，导致导出功能的 frontmatter 字段为空。

## What Changes

- Claude LLM 的 `_extract_frames` 改用 timestamp seeking 方式（与 OpenAI LLM 一致），添加超时保护
- Whisper 设备检测增加运行时 CUDA 失败后的永久回退逻辑，OOM 时自动切换到 CPU 并缓存
- Pipeline 中将 classification 结果（content_type、language）存入数据库 metadata 字段
- 导出 Markdown 功能自动填充 content_type 和 language 字段

## Capabilities

### New Capabilities
- `cuda-fallback`: Whisper 在 CUDA OOM 时永久回退到 CPU，避免重复失败
- `claude-frame-extraction`: Claude LLM 使用 timestamp seeking 提取帧，与 OpenAI LLM 行为一致
- `store-classification`: Pipeline 将分类结果持久化到数据库

### Modified Capabilities

（无）

## Impact

- `core/asr/whisper.py` — 修改 `_get_device()` 和 `transcribe()` 添加 CUDA 回退逻辑
- `core/llm/claude.py` — 重写 `_extract_frames()` 使用 timestamp seeking + 超时
- `core/pipeline.py` — 在 classify 后将 content_type/language 写入 metadata
- `core/storage/db.py` — 无需改动（metadata 字段已是 JSON dict）
- `core/web/app.js` — `generateObsidianMarkdown()` 从 metadata 读取 content_type/language
