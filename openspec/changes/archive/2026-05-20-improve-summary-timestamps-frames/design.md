## Context

三个独立问题：
1. `detail` 参数贯穿 pipeline 但从未影响输出
2. Whisper segments 有精确时间信息但被丢弃
3. `_download_video_stream` 与 `download` 有相同的 `_filename` bug

## Goals / Non-Goals

**Goals:**
- `detail=detailed` 生成更详尽的摘要
- 转录文本包含 `[MM:SS]` 时间戳
- multimodal 模式帧提取正常工作

**Non-Goals:**
- 不做 word-level 时间戳（段落级足够）
- 不改变 whisper 模型选择逻辑
- 不改变 LLM provider

## Decisions

### 1. Detail 级别实现方式

在 prompt 模板末尾追加指令：
- `brief`: "请用 2-3 句话概括核心内容"
- `normal`: 当前默认行为
- `detailed`: "请提供详尽分析，包含具体例子、数据引用、时间点"

同时调整 max_tokens: brief=1024, normal=4096, detailed=8192。

### 2. 时间戳格式

faster-whisper segments 的 `.start` 是秒数浮点数。格式化为 `[MM:SS]`：
```python
f"[{int(start//60):02d}:{int(start%60):02d}] {text}"
```

每段一行，保持可读性。返回类型从 `str` 改为 `str`（格式化后），不需要改接口。

### 3. 帧提取修复

在 `_download_video_stream` 中应用与 `download` 相同的修复：
```python
vid_file = Path(vid_info.get("_filename") or "")
if not vid_file.name or not vid_file.exists():
```

## Risks / Trade-offs

- [时间戳增加 token] 格式化后文本略长 → 对 LLM 影响可忽略
- [detail 指令] 可能不够精确 → 用户可通过 prompt 定制进一步调整
