## 1. 轻量列表查询

- [x] 1.1 在 `db.py` 中添加 `list_tasks_light` 方法，仅返回 task_id, url, platform, status, created_at, favorite, progress, metadata
- [x] 1.2 在 `db.py` 中为 `created_at` 添加索引
- [x] 1.3 在 `routes.py` 中修改 `list_tasks` 使用 `list_tasks_light`
- [x] 1.4 在 `db.py` 中添加 `get_task_status` 方法，仅返回 status 和 progress
- [x] 1.5 在 `routes.py` 中添加 `GET /api/tasks/{id}/status` 轻量轮询端点
- [x] 1.6 在 `app.js` 中修改轮询使用轻量端点

## 2. 并行下载

- [x] 2.1 在 `base.py` 的 `download` 方法中使用 ThreadPoolExecutor 并行下载音频和视频流
- [x] 2.2 处理视频下载失败的降级逻辑

## 3. LLM 流式响应

- [x] 3.1 在 `base.py` (LLM) 中添加 `_chat_stream` 抽象方法
- [x] 3.2 在 `openai_proto.py` 中实现 `_chat_stream`（使用 stream=True）
- [x] 3.3 在 `routes.py` 中添加 SSE 流式端点
- [x] 3.4 在 `app.js` 中实现流式内容显示

## 4. 测试

- [x] 4.1 验证轻量列表不包含 transcript/summary
- [x] 4.2 验证轻量轮询端点返回正确格式
- [x] 4.3 验证并行下载降级逻辑
