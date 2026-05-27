## Why

项目存在多个可靠性和用户体验问题：平台下载代码高度重复（Bilibili/YouTube ~95% 相同）、任务失败后无法重试只能重新提交、前端无进度细分导致长时间操作看起来卡死、历史记录无搜索过滤功能、SQLite 无 WAL 模式在并发时可能锁定、下载无重试机制。随着任务数量增长，这些问题的影响会持续放大。

## What Changes

- **平台代码重构**：提取 Bilibili/YouTube 共享逻辑到 `YtdlpPlatform` 基类，消除 ~80 行重复代码
- **任务重试**：失败任务支持一键重试，复用已有 task_id 重新执行 pipeline
- **进度细分**：pipeline 各阶段报告百分比进度（下载/转录/帧提取/总结），前端展示阶段内进度条
- **历史搜索过滤**：前端 history 表格支持按标题搜索、按平台/状态筛选
- **SQLite WAL 模式**：启动时设置 `PRAGMA journal_mode=WAL`，避免并发读写锁定
- **下载重试**：yt-dlp 下载失败时自动重试（最多 3 次）

## Capabilities

### New Capabilities
- `platform-refactor`: 提取 yt-dlp 平台共享逻辑到基类，Bilibili/YouTube 只保留 URL 匹配和 cookies 差异
- `task-retry`: 失败任务支持一键重试，前端显示重试按钮，后端支持重新执行 pipeline
- `progress-granularity`: pipeline 各阶段报告子进度百分比，前端展示阶段内进度
- `history-search-filter`: 前端 history 表格支持标题搜索和平台/状态筛选
- `sqlite-wal`: 启用 SQLite WAL 模式提升并发读写性能
- `download-retry`: yt-dlp 下载失败时自动重试，最多 3 次指数退避

### Modified Capabilities

（无）

## Impact

- `core/platforms/base.py` — 新增 `YtdlpPlatform` 基类
- `core/platforms/bilibili.py` — 重构继承 `YtdlpPlatform`，只保留 URL 匹配和 cookies
- `core/platforms/youtube.py` — 重构继承 `YtdlpPlatform`
- `core/pipeline.py` — 添加子进度报告、下载重试逻辑
- `core/storage/db.py` — 启用 WAL 模式、添加 `reset_task()` 方法
- `core/api/routes.py` — 添加重试端点
- `core/web/index.html` — 重试按钮、搜索/筛选 UI
- `core/web/app.js` — 重试逻辑、进度细分、搜索过滤功能
- `core/web/style.css` — 搜索/筛选样式
