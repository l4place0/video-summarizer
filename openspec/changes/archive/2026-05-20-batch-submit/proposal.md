## Why

用户经常需要一次性总结多个视频（如一个系列的教程、一个频道的最新视频）。当前架构只支持单个 URL 提交，用户必须重复 submit → wait → submit 流程，效率低下。批量提交功能允许用户一次输入多个 URL，系统自动排队处理，用户可以继续做其他事情。

## What Changes

- **前端输入**：将单行 URL 输入框改为支持多行输入（textarea），每行一个 URL
- **批量 API**：新增 `POST /api/summarize/batch` 端点，接受 URL 列表，返回多个 task_id
- **批量进度**：前端显示批量提交的整体进度（已完成/总数）
- **URL 验证**：提交前在前端验证每个 URL 的格式，跳过无效 URL
- **错误隔离**：单个 URL 失败不影响其他 URL 的处理

## Capabilities

### New Capabilities
- `batch-submit`: 支持一次提交多个视频 URL，系统自动排队并行处理，前端显示批量进度

### Modified Capabilities

（无）

## Impact

- `core/api/routes.py` — 新增 `/api/summarize/batch` 端点
- `core/models.py` — 新增 `BatchSummarizeRequest` 和 `BatchTaskResponse` 模型
- `core/web/index.html` — URL 输入改为 textarea + 批量提交按钮
- `core/web/app.js` — 批量提交逻辑、批量进度显示
- `core/web/style.css` — textarea 和批量进度样式
