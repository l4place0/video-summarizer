## 1. 数据埋点

- [x] 1.1 在 `pipeline.py` 中创建 MetricsTracker 类，记录各阶段开始/结束时间
- [x] 1.2 在 pipeline 各阶段（download、transcribe、extract_frames、classify、summarize）调用 tracker
- [x] 1.3 在 pipeline 结束时将 metrics 写入 task metadata

## 2. 模型和 API

- [x] 2.1 在 `models.py` 中添加 PipelineMetrics 和 StageMetrics 模型（metrics 存储在 metadata 中，无需独立模型）
- [x] 2.2 在 `routes.py` 的任务详情响应中包含 metrics 字段（已通过 metadata 字段返回）

## 3. WebUI 展示

- [x] 3.1 在 `index.html` 中添加 metrics 展示区域
- [x] 3.2 在 `app.js` 中实现 metrics 渲染逻辑（条形图 + 数值）
- [x] 3.3 在 `style.css` 中添加 metrics 样式

## 4. 测试

- [x] 4.1 验证 metrics 数据结构正确
- [x] 4.2 验证 metrics 在 API 响应中包含
