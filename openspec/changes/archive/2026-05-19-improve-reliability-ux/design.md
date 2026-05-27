## Context

项目有 6 个已识别的改进点，按优先级排列：

1. **平台代码重复**：`bilibili.py` 和 `youtube.py` 的 `download()` 方法有相同的 yt-dlp 配置、metadata 提取、视频流下载逻辑，仅 URL 匹配和 cookies 不同。
2. **任务失败无法重试**：pipeline 失败后只能重新提交 URL，无法复用已有 task_id。
3. **进度无细分**：前端只显示阶段标签，长时间操作（如转录 30min 视频）看起来卡死。
4. **历史无搜索**：15+ 任务，无按标题/平台/状态筛选能力。
5. **SQLite 无 WAL**：默认 journal 模式在并发读写时可能 "database is locked"。
6. **下载无重试**：yt-dlp 网络请求失败直接报错，无自动重试。

## Goals / Non-Goals

**Goals:**
- 消除 Bilibili/YouTube 之间的重复代码
- 失败任务支持一键重试，不改变 task_id
- pipeline 各阶段报告子进度百分比
- 前端 history 支持标题搜索和平台/状态筛选
- SQLite 启用 WAL 模式
- yt-dlp 下载失败自动重试（最多 3 次）

**Non-Goals:**
- 不做异步任务队列（Celery/RQ）— 保持 threading 模式
- 不做 WebSocket 实时推送 — 保持轮询
- 不做批量 URL 提交
- 不做自动测试框架搭建

## Decisions

### 1. 平台重构：YtdlpPlatform 基类

提取共享逻辑到 `base.py` 的 `YtdlpPlatform` 类：

```
YtdlpPlatform(BasePlatform)
├── download()          — 共享的 yt-dlp 下载逻辑
├── _get_ydl_opts()     — 子类可覆盖（cookies 等）
├── _build_metadata()   — 共享的 metadata 提取
├── _download_video()   — 共享的视频流下载
└── match() / parse_url() — 子类必须实现

BilibiliPlatform(YtdlpPlatform)
├── match()             — bilibili URL 匹配
├── parse_url()         — BV 号提取
└── _get_ydl_opts()     — 添加 cookies

YouTubePlatform(YtdlpPlatform)
├── match()             — youtube URL 匹配
└── parse_url()         — video ID 提取
```

**理由：** 最小改动，保留子类扩展点，不改变外部接口。

### 2. 任务重试：reset_task() + 重试端点

新增 `db.reset_task(task_id)` 方法：将 status 重置为 "pending"，清空 summary/transcript/error/completed_at，保留 metadata 和 url。

新增 `POST /api/tasks/{task_id}/retry` 端点：调用 reset_task() 后启动新 pipeline thread。

前端：失败任务的 result-actions 区域显示 "Retry" 按钮。

**理由：** 复用 task_id 避免创建重复记录，保留原始 metadata。

### 3. 进度细分：阶段内百分比

pipeline 各阶段通过 `db.update_task()` 写入 `progress` 字段（0-100）：

```
pending:     0%
downloading: 10-25%  (yt-dlp progress hook)
transcribing: 25-50%  (基于音频时长估算)
extracting_frames: 50-70%  (已完成帧数/总帧数)
classifying: 70-80%
summarizing: 80-95%
done:        100%
```

前端：在 status-text 旁显示阶段内百分比。

**理由：** 利用现有 metadata JSON 字段，无需 schema 迁移。yt-dlp 有 `progress_hooks` 支持。

### 4. 历史搜索过滤：纯前端

在 history 表格上方添加搜索框和筛选下拉框（平台、状态），使用 JavaScript 过滤已加载的 tasks 数组。

**理由：** 任务量小（<100），纯前端过滤足够，无需后端 API 改动。

### 5. SQLite WAL：启动时 PRAGMA

在 `Storage.__init__()` 中添加 `PRAGMA journal_mode=WAL`。

**理由：** 一行代码，显著提升并发读写性能，WAL 模式是 SQLite 的推荐配置。

### 6. 下载重试：指数退避

在 `YtdlpPlatform.download()` 中包装 yt-dlp 调用，失败时等待 2s/4s/8s 后重试，最多 3 次。

**理由：** 网络抖动是常见失败原因，简单重试可以解决大部分问题。

## Risks / Trade-offs

- [WAL 副作用] WAL 模式会创建 `-wal` 和 `-shm` 文件 → 正常行为，备份时需一起拷贝
- [重试覆盖] 重试会覆盖之前的 metadata → 可接受，重试意味着之前的数据不可用
- [进度精度] yt-dlp progress_hooks 不是所有下载器都支持 → 无 hook 时使用离散步进（10%/15%/20%）
- [前端过滤] 纯前端过滤只对已加载的任务有效 → 当前一次性加载所有任务，足够用
