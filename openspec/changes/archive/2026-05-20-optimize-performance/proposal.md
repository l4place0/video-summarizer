## Why

当前系统存在三类性能瓶颈：
1. **历史列表加载慢** — `list_tasks` 返回所有字段（含 transcript/summary 大文本），前端仅需标题/状态/标签
2. **multimodal 下载串行** — 音频和视频流顺序下载，浪费 30-60s
3. **LLM 响应延迟高** — 同步等待完整响应，用户等待 15-40s 无反馈

## What Changes

- **DB 查询优化** — list_tasks 不加载 transcript/summary，添加 created_at 索引
- **并行下载** — multimodal 模式下音频和视频流并行下载
- **LLM 流式响应** — classify 和 summarize 支持 streaming，前端实时显示
- **轮询轻量化** — 历史列表轮询只查 status/progress，不传全文

## Capabilities

### New Capabilities

- `lightweight-task-listing`: list_tasks 返回轻量字段，避免加载大文本
- `parallel-stream-download`: multimodal 模式音频+视频并行下载
- `llm-streaming`: LLM 响应流式传输，前端实时显示

### Modified Capabilities

（无）

## Impact

- `core/storage/db.py` — 新增 list_tasks_light 方法、添加索引
- `core/api/routes.py` — list_tasks 使用轻量查询、新增 streaming 端点
- `core/platforms/base.py` — 并行下载音频和视频流
- `core/llm/openai_proto.py` — 支持 streaming 模式
- `core/llm/claude.py` — 支持 streaming 模式
- `core/llm/base.py` — 添加 _chat_stream 抽象方法
- `core/web/app.js` — 流式显示 LLM 输出
- `core/models.py` — 新增轻量 TaskListItem 模型
