# Phase 01 — Backend Core

## 目标
构建完整的后端服务，支持视频摘要的端到端流程。

## 模块清单

### 1. 项目结构 & 基础设施
- FastAPI 应用入口 (`app/main.py`)
- 配置管理 (`app/core/config.py`) — 环境变量，LLM key，路径
- 数据模型 (`app/core/models.py`) — Pydantic schema
- Docker + docker-compose
- requirements.txt

### 2. 存储层 (`app/storage.py`)
- SQLite：任务表 (id, url, platform, status, summary, created_at, metadata)
- 文件管理：audio/ transcripts/ 目录
- 清理 API：按时间清理、全量清理、占用查询

### 3. 平台层 (`app/platforms/`)
- 抽象基类 `BasePlatform`
  - `download(url) -> (audio_path, metadata)`
  - `extract_audio(video_path) -> audio_path`
  - `parse_url(url) -> video_id`
- Bilibili 实现 (`bilibili.py`) — yt-dlp 下载 + ffmpeg 提取音频

### 4. ASR 层 (`app/asr/`)
- Whisper 封装
- `transcribe(audio_path, language) -> transcript`

### 5. LLM 层 (`app/llm/`)
- 抽象基类 `BaseLLM`
  - `summarize(transcript, prompt, lang) -> summary`
- Claude 实现 — Anthropic SDK，支持自定义 `ANTHROPIC_BASE_URL`
- OpenAI 协议实现 — 兼容 OpenAI API 格式，支持自定义 `OPENAI_BASE_URL`

### 6. Pipeline (`app/core/pipeline.py`)
- 编排：download → transcribe → summarize
- 状态流转：pending → downloading → transcribing → summarizing → done / failed
- 入库记录

### 7. API 路由

#### GET /health
```json
// Response 200
{ "status": "ok", "version": "0.1.0" }
```

#### POST /api/summarize
提交视频 URL，异步处理，返回任务 ID。

**Request:**
```json
{
  "url": "https://www.bilibili.com/video/BV1xx411c7XW",
  "language": "zh",
  "llm_provider": "claude",
  "detail": "normal"
}
```

| Field         | Type   | Default  | Description       |
|--------------|--------|----------|-------------------|
| url          | string | required | 视频 URL           |
| language     | string | "zh"     | ASR 语言           |
| llm_provider | string | "claude" | claude / openai    |
| detail       | string | "normal" | normal / detailed  |

**Response 202:**
```json
{ "task_id": "uuid", "status": "pending" }
```

#### GET /api/tasks
```json
// Response 200
{
  "tasks": [
    {
      "task_id": "uuid",
      "url": "...",
      "platform": "bilibili",
      "status": "done",
      "summary": "...",
      "created_at": "2026-05-13T10:00:00Z",
      "metadata": { "title": "...", "duration": 300 }
    }
  ]
}
```

#### GET /api/tasks/{task_id}
```json
// Response 200
{
  "task_id": "uuid",
  "url": "...",
  "platform": "bilibili",
  "status": "done",
  "summary": "...",
  "transcript": "...",
  "created_at": "...",
  "completed_at": "...",
  "metadata": {}
}
```

**Status 流转:** `pending → downloading → transcribing → summarizing → done | failed`

#### GET /api/storage
```json
// Response 200
{
  "db_size_bytes": 102400,
  "cache_size_bytes": 52428800,
  "task_count": 12
}
```

#### DELETE /api/storage
**Query params:**

| Param      | Type   | Description         |
|-----------|--------|---------------------|
| older_than | string | 如 "7d"，清理 N 天前 |

```json
// Response 200
{ "deleted_files": 5, "deleted_tasks": 3, "freed_bytes": 52428800 }
```

## 验收标准

### 功能验收

| # | 场景 | 验证方式 | 预期结果 |
|---|------|---------|---------|
| 1 | 服务启动 | `docker compose up` | 容器正常运行，无报错 |
| 2 | 健康检查 | `curl localhost:8000/health` | 200, `{"status":"ok"}` |
| 3 | 端到端摘要 | 提交 B 站视频 URL | 状态流转完成，返回中文摘要 |
| 4 | 任务查询 | `GET /api/tasks` 和 `GET /api/tasks/{id}` | 返回任务列表和详情 |
| 5 | 存储查询 | `GET /api/storage` | 返回 db/cache 大小和任务数 |
| 6 | 存储清理 | `DELETE /api/storage` | 文件和记录被清除 |
| 7 | 按时间清理 | `DELETE /api/storage?older_than=7d` | 仅清理指定时间前的数据 |

### 错误处理验收

| # | 场景 | 预期结果 |
|---|------|---------|
| E1 | 无效 URL / 非 B 站链接 | 400 + 明确错误信息 |
| E2 | LLM API key 未配置 | 启动时或调用时明确报错 |
| E3 | 下载失败 / 网络超时 | 任务状态 → failed，错误信息可查 |
| E4 | Whisper 模型加载失败 | 明确报错，不影响其他功能 |

### 非功能验收

| 维度 | 要求 |
|------|------|
| 性能 | pipeline 不卡死，异步处理不阻塞 API |
| 日志 | 面向用户只展示 pipeline 进度（downloading/transcribing/summarizing） |

### 测试方式

1. **pytest** — 单元测试用 mock，集成测试需真实 API key（无 key 自动 skip）
2. **curl 命令** — 提供手动验证的完整命令序列
3. **自检脚本** — `scripts/self_check.sh`，自动跑全链路并输出报告

### 验收命令

```bash
# 1. 跑单元测试
source .venv/bin/activate
python -m pytest tests/ -v

# 2. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000
# 或 docker compose up

# 3. 手动 curl 验证
curl localhost:8000/health
curl localhost:8000/api/tasks
curl localhost:8000/api/storage

# 提交视频，用 jq 提取完整 task_id
TASK_ID=$(curl -s -X POST localhost:8000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.bilibili.com/video/BV1xx411c7XW"}' | jq -r '.task_id')

# 轮询状态（会经历 downloading → transcribing → summarizing → done）
curl -s "localhost:8000/api/tasks/$TASK_ID" | jq .

# 查看所有任务
curl -s localhost:8000/api/tasks | jq .

# 清理存储
curl -s -X DELETE localhost:8000/api/storage | jq .
```

### 自检结果 (2026-05-13)

- [x] pytest: 27/27 passed, 0 warnings (17 unit + 10 integration)
- [x] 服务启动: clean startup/shutdown
- [x] 集成测试覆盖:
  - 成功路径 (Claude + OpenAI provider)
  - 状态流转 (downloading → transcribing → summarizing → done)
  - 错误路径 (download 失败, LLM 失败 → status=failed)
  - 存储查询 + 清理
  - 边界情况 (无效 URL, 任务不存在)

### 已知环境问题

| 问题 | 影响 | 解决方式 |
|------|------|---------|
| 未安装 ffmpeg | 无法提取音频 | `apt install ffmpeg` 或用 Docker |
| 未配置 LLM API key | 无法生成摘要 | 在 `.env` 中配置 key |
| Whisper 首次运行需下载模型 | 首次转录较慢 (~139MB) | 自动下载，后续缓存 |
