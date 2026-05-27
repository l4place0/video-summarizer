## Why

当前系统无法追踪每个环节的资源消耗（时间、API 调用次数、token 用量、文件大小等），无法定位性能瓶颈，也无法量化优化效果。

## What Changes

- **数据埋点** — 在 pipeline 每个阶段记录时间戳、耗时、资源用量
- **Metrics 模型** — 定义结构化的 metrics 数据结构，存储到任务 metadata
- **WebUI 展示** — 在任务详情页显示各阶段耗时和资源用量图表
- **API 端点** — 提供 metrics 查询接口

## Capabilities

### New Capabilities

- `pipeline-metrics`: Pipeline 各阶段资源用量追踪和展示

### Modified Capabilities

（无）

## Impact

- `core/pipeline.py` — 每个阶段记录 metrics
- `core/models.py` — 添加 PipelineMetrics 模型
- `core/api/routes.py` — metrics 查询端点
- `core/web/app.js` — metrics 展示逻辑
- `core/web/index.html` — metrics UI 容器
- `core/web/style.css` — metrics 样式
