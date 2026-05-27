## Context

系统 pipeline 总耗时 3-5 分钟（10 分钟视频），其中：
- Transcription 60-120s（已并行帧提取）
- Download 30-60s（multimodal 模式串行下载音频+视频）
- LLM 15-40s（同步等待完整响应）
- 历史列表加载含全文 transcript（数百 KB），前端仅需元数据

## Goals / Non-Goals

**Goals:**
- list_tasks 返回 <10KB（当前可能 >100KB）
- multimodal 下载时间减少 30-50%
- LLM 首字响应 <5s（流式）

**Non-Goals:**
- 不改变 Whisper 转录逻辑
- 不引入 WebSocket（用 SSE 替代）
- 不做 LLM 结果缓存

## Decisions

### 1. 轻量列表查询

新增 `list_tasks_light` 方法，仅返回 task_id, url, platform, status, created_at, favorite, progress, metadata（不含 transcript/summary/error）。

前端 history 页使用此方法，viewTask 时再加载完整数据。

**替代方案：** 分页查询（当前规模不需要）

### 2. 并行下载

在 `download` 方法中使用 `ThreadPoolExecutor` 并行执行音频下载和视频流下载。

```
当前:  Audio ──30s──▶ Extract ──5s──▶ Video ──30s──▶ Done
并行:  Audio ──30s──▶ Extract     Video ──30s──▶
                    └──────── 等待两者完成 ──────┘▶ Done
```

节省约 30s（视频流下载时间）。

### 3. LLM 流式响应

添加 `_chat_stream` 方法，使用 OpenAI `stream=True`。Pipeline 中 summarize 使用流式模式，通过 SSE 推送到前端。

**替代方案：** WebSocket（过度复杂）、轮询中间结果（延迟高）

### 4. 轮询轻量化

新增 `GET /api/tasks/{id}/status` 端点，仅返回 status + progress。前端轮询使用此端点。

## Risks / Trade-offs

- [流式 SSE] 增加前后端复杂度 → 但用户体验提升显著
- [并行下载] 两个线程同时占用带宽 → 当前场景可接受
- [轻量查询] 需要维护两套查询方法 → 简单实现，可接受
