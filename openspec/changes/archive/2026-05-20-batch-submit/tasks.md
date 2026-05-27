## 1. 后端 API

- [x] 1.1 在 `models.py` 中添加 `BatchSummarizeRequest` 和 `BatchTaskResponse` 模型
- [x] 1.2 在 `routes.py` 中添加 `POST /api/summarize/batch` 端点

## 2. 前端输入

- [x] 2.1 在 `index.html` 中将 URL input 改为 textarea，添加 placeholder 提示
- [x] 2.2 在 `style.css` 中添加 textarea 样式

## 3. 前端逻辑

- [x] 3.1 在 `app.js` 中实现批量提交逻辑（分割 URL、验证、调用 batch API）
- [x] 3.2 在 `app.js` 中实现批量进度显示（计数器、每个 task 独立轮询）
- [x] 3.3 在 `app.js` 中实现 URL 验证（匹配已知平台）

## 4. 测试

- [x] 4.1 验证单个 URL 提交行为不变
- [x] 4.2 验证批量提交多个 URL 创建多个 task
- [x] 4.3 验证无效 URL 被跳过并报告
- [x] 4.4 验证批量进度计数器正确更新
