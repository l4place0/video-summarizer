## Context

当前架构每次只能提交一个视频 URL。用户需要批量处理多个视频时，必须手动重复 submit → wait → submit 流程。批量功能需要在不改变现有单个提交流程的前提下，支持多 URL 同时提交。

## Goals / Non-Goals

**Goals:**
- 支持一次提交多个 URL（textarea 输入，每行一个）
- 每个 URL 独立创建 task，互不影响
- 前端显示批量进度（已完成/总数、每个 task 的状态）
- 提交前前端验证 URL 格式，跳过无效 URL
- 失败的 task 不阻塞其他 task

**Non-Goals:**
- 不做后端队列系统（保持 threading 模式）
- 不做 URL 去重（用户可能有意重复提交）
- 不做批量导出（仅批量提交）
- 不做进度聚合（每个 task 独立轮询）

## Decisions

### 1. 输入方式：textarea 替换 input

将 `#url-input` 从 `<input type="text">` 改为 `<textarea>`，每行一个 URL。前端按行分割，过滤空行，验证每个 URL。

**理由：** 最简单的 UX，用户可以直接从文档/列表粘贴多个 URL。

### 2. API 设计：批量端点

新增 `POST /api/summarize/batch`：
```json
// Request
{"urls": ["url1", "url2", ...], "language": "zh", "llm_provider": "openai", "mode": "multimodal"}

// Response
{
  "tasks": [
    {"task_id": "xxx", "url": "url1", "status": "pending"},
    {"task_id": "yyy", "url": "url2", "status": "pending"}
  ],
  "skipped": ["invalid_url"]
}
```

**理由：** 单次请求创建多个 task，返回所有 task_id。跳过的无效 URL 在 `skipped` 中报告。

### 3. 并行处理：每 URL 一个线程

每个 URL 启动独立的 `threading.Thread` 运行 pipeline。无并发限制。

**理由：** 现有架构已经是 threading 模式，批量提交只是多启动几个线程。pipeline 内部有 I/O 等待（下载、API 调用），线程不会真正并行占用 CPU。

### 4. 前端进度：复用现有轮询

提交后，前端为每个 task_id 启动独立的 `setInterval` 轮询。批量进度显示为 "X/Y done"。

**理由：** 复用现有的 `pollTask` 逻辑，最小改动。每个 task 独立更新，无需聚合。

### 5. URL 验证：前端预检

提交前检查每个 URL 是否匹配已知平台（Bilibili/YouTube）。不匹配的 URL 加入 skipped 列表。

**理由：** 减少无效请求，快速反馈给用户。

## Risks / Trade-offs

- [线程数] 大量 URL 可能创建过多线程 → 当前场景（<20 个 URL）可接受，未来可加线程池限制
- [前端轮询] 每个 task 独立轮询，大量 URL 会产生很多请求 → 轮询间隔 2s，20 个 URL = 10 req/s，可接受
- [textarea UX] 用户可能不知道每行一个 URL 的格式 → placeholder 提示 + 提交时验证反馈
