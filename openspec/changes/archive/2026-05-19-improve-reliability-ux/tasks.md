## 1. SQLite WAL 模式

- [x] 1.1 在 `Storage.__init__()` 中添加 `PRAGMA journal_mode=WAL`

## 2. 平台代码重构

- [x] 2.1 在 `base.py` 中创建 `YtdlpPlatform` 基类，提取共享的 `download()`、`_get_ydl_opts()`、`_build_metadata()`、`_download_video_stream()` 方法
- [x] 2.2 重构 `bilibili.py` 继承 `YtdlpPlatform`，仅覆盖 URL 匹配、解析和 cookies
- [x] 2.3 重构 `youtube.py` 继承 `YtdlpPlatform`，仅覆盖 URL 匹配和解析

## 3. 下载重试

- [x] 3.1 在 `YtdlpPlatform.download()` 中添加重试逻辑（最多 3 次，指数退避 2s/4s/8s）
- [x] 3.2 视频流下载也使用相同的重试逻辑

## 4. 任务重试

- [x] 4.1 在 `db.py` 中添加 `reset_task(task_id)` 方法（重置 status/summary/transcript/error/completed_at）
- [x] 4.2 在 `routes.py` 中添加 `POST /api/tasks/{task_id}/retry` 端点
- [x] 4.3 在 `index.html` 中添加 "Retry" 按钮
- [x] 4.4 在 `app.js` 中添加重试按钮事件绑定和可见性控制

## 5. 进度细分

- [x] 5.1 在 `pipeline.py` 中为 downloading 阶段添加子进度报告（10-25%）
- [x] 5.2 在 `pipeline.py` 中为 transcribing 阶段添加子进度报告（25-50%）
- [x] 5.3 在 `pipeline.py` 中为 extracting_frames 阶段添加子进度报告（50-70%）
- [x] 5.4 在 `pipeline.py` 中为 classifying/summarizing 阶段添加子进度报告（75%/90%）
- [x] 5.5 在 `app.js` 的 `updateResult()` 中显示阶段内百分比

## 6. 历史搜索过滤

- [x] 6.1 在 `index.html` 的 history 表格上方添加搜索框和筛选下拉框（平台、状态）
- [x] 6.2 在 `app.js` 中实现搜索和筛选逻辑（纯前端过滤已加载数据）
- [x] 6.3 在 `style.css` 中添加搜索/筛选 UI 样式

## 7. 测试

- [x] 7.1 验证平台重构后 Bilibili/YouTube 下载功能正常
- [x] 7.2 验证失败任务重试功能
- [x] 7.3 验证进度百分比显示
- [x] 7.4 验证历史搜索和筛选功能
- [x] 7.5 验证 SQLite WAL 模式生效
