# Bilibili Learning Helper

[English](README_EN.md) | 中文

基于 Whisper ASR + LLM 的 Bilibili/YouTube 视频摘要工具。

## 功能特性

- **视频摘要** — 自动下载、转录、分类、总结视频内容
- **批量处理** — 支持一次提交多个 URL，批量生成摘要
- **分享链接解析** — 直接粘贴 Bilibili 分享链接（含标题前缀）即用
- **多语言** — 支持中文、英文、日文视频
- **多 LLM** — 支持 OpenAI / Claude
- **多模态** — 可选帧分析模式，结合画面内容生成更丰富摘要
- **Markdown 导出** — 一键导出 Obsidian 兼容的 YAML frontmatter 格式
- **历史管理** — 搜索、筛选、收藏、重试、删除任务
- **Prompt 定制** — 自定义分类和摘要提示词
- **Web UI** — 现代化暗色主题界面

## 快速开始

### 环境要求

- Python 3.10+
- ffmpeg
- yt-dlp

### 安装

```bash
# 克隆仓库
git clone https://github.com/l4place/bilibili-learning-helper.git
cd bilibili-learning-helper

# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API Key
```

### 启动

```bash
uv run uvicorn core.main:app --port 8000
```

打开浏览器访问 `http://localhost:8000`

### 使用 Skill

```bash
# 单个视频
bash skill/scripts/summarize.sh "https://bilibili.com/video/BVxxxxx"

# 批量提交
bash skill/scripts/summarize.sh "url1" "url2" "url3"

# 检查状态
bash skill/scripts/status.sh

# 检查更新
bash skill/scripts/check-update.sh
```

## Docker 部署

```bash
docker compose up -d
```

## 技术架构

```
用户输入 URL
    │
    ▼
┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Download │──▶│  Whisper  │──▶│ Classify │──▶│ Summarize│
│ (yt-dlp) │   │  (ASR)   │   │  (LLM)   │   │  (LLM)   │
└─────────┘   └──────────┘   └──────────┘   └──────────┘
                  │                              │
                  ▼                              ▼
            转录文本                        结构化摘要
```

### 内容类型路由

系统先将视频分为 7 种类型，然后使用对应的结构化提示词：

| 类型 | 说明 | 输出结构 |
|------|------|----------|
| tutorial | 教程 | 步骤、前置条件、常见问题 |
| tech_talk | 技术演讲 | 核心论点、证据、展望 |
| demo | 产品演示 | 工作流、输入输出、优缺点 |
| review | 评测对比 | 对象、标准、推荐 |
| news | 新闻 | 事实、背景、观点 |
| vlog | 日常 | 场景、亮点 |
| general | 通用 | 核心内容、要点、分析 |

## API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/summarize` | POST | 提交视频摘要 |
| `/api/summarize/batch` | POST | 批量提交 |
| `/api/tasks` | GET | 任务列表 |
| `/api/tasks/{id}` | GET | 任务详情 |
| `/api/tasks/{id}/status` | GET | 轻量状态轮询 |
| `/api/tasks/{id}/stream` | GET | SSE 流式输出 |
| `/api/storage` | GET | 存储信息 |
| `/api/storage` | DELETE | 清理数据 |

## 配置

环境变量（`.env`）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | | OpenAI/MIMO API Key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API 端点 |
| `OPENAI_MODEL` | `gpt-4o` | 文本模型 |
| `OPENAI_VISION_MODEL` | | 视觉模型（多模态） |
| `ANTHROPIC_API_KEY` | | Claude API Key |
| `WHISPER_MODEL` | `base` | Whisper 模型大小 |
| `MAX_FRAMES` | `10` | 多模态最大帧数 |

## 技术栈

- Python 3.10+, FastAPI, uv
- Whisper (ASR), yt-dlp (下载), ffmpeg (音视频处理)
- Claude / OpenAI 兼容 LLM
- SQLite (WAL 模式)

## 许可证

MIT License
