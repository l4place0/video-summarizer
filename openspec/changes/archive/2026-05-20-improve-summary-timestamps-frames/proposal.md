## Why

1. **总结不够详尽** — `detail` 参数是死参数，`brief`/`normal`/`detailed` 返回相同的 prompt，max_tokens 硬编码 4096
2. **转录无时间戳** — faster-whisper 的 segments 有 `.start`/`.end` 时间信息，但代码只拼接 `.text`，丢弃了时间戳
3. **帧提取为空** — `_download_video_stream` 中 `_filename` 为空时 `Path("").exists()` 为 True（当前目录），跳过 glob 回退，导致 ffmpeg 对目录提取帧失败

## What Changes

- **detail 生效** — 在 prompt 模板中添加 detail 指令，根据级别调整输出要求
- **时间戳转录** — 转录返回带时间戳的格式化文本 `[MM:SS] 文本`
- **帧提取修复** — `_download_video_stream` 应用同样的 `name` 检查

## Capabilities

### New Capabilities

- `timestamped-transcription`: 转录输出包含段落级时间戳
- `detail-level-prompts`: summary prompt 根据 detail 参数调整详细度

### Modified Capabilities

（无）

## Impact

- `core/llm/prompts.py` — 添加 detail 级别指令到 prompt 模板
- `core/llm/openai_proto.py` — 根据 detail 调整 max_tokens
- `core/asr/whisper.py` — 返回带时间戳的格式化文本
- `core/platforms/base.py` — 修复 `_download_video_stream` 的 `_filename` bug
