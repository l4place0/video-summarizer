# Bilibili Learning Helper

English | [中文](README.md)

A video summarization tool powered by Whisper ASR + LLM for Bilibili and YouTube.

## Features

- **Video Summarization** — Automatically download, transcribe, classify, and summarize video content
- **Batch Processing** — Submit multiple URLs at once, generate summaries in parallel
- **Share Link Parsing** — Paste Bilibili share links (with title prefix) directly
- **Multi-language** — Supports Chinese, English, and Japanese videos
- **Multi-LLM** — Supports OpenAI and Claude
- **Multimodal** — Optional frame analysis mode for richer visual-aware summaries
- **Markdown Export** — One-click export to Obsidian-compatible YAML frontmatter format
- **History Management** — Search, filter, favorite, retry, and delete tasks
- **Prompt Customization** — Customize classification and summary prompts
- **Web UI** — Modern dark-themed interface

## Quick Start

### Prerequisites

- Python 3.10+
- ffmpeg
- yt-dlp

### Installation

```bash
# Clone the repository
git clone https://github.com/l4place/bilibili-learning-helper.git
cd bilibili-learning-helper

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Start

```bash
uv run uvicorn core.main:app --port 8000
```

Open browser at `http://localhost:8000`

### Skill Usage

```bash
# Single video
bash skill/scripts/summarize.sh "https://bilibili.com/video/BVxxxxx"

# Batch submit
bash skill/scripts/summarize.sh "url1" "url2" "url3"

# Check status
bash skill/scripts/status.sh

# Check for updates
bash skill/scripts/check-update.sh
```

## Docker Deployment

```bash
docker compose up -d
```

## Architecture

```
User submits URL
    │
    ▼
┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│ Download │──▶│  Whisper  │──▶│ Classify │──▶│ Summarize│
│ (yt-dlp) │   │  (ASR)   │   │  (LLM)   │   │  (LLM)   │
└─────────┘   └──────────┘   └──────────┘   └──────────┘
                  │                              │
                  ▼                              ▼
            Transcript                   Structured Summary
```

### Content Type Routing

The system classifies videos into 7 types, then applies tailored prompts:

| Type | Description | Output Structure |
|------|-------------|------------------|
| tutorial | How-to guides | Steps, prerequisites, pitfalls |
| tech_talk | Tech speeches | Core argument, evidence, outlook |
| demo | Product demos | Workflow, input/output, strengths |
| review | Comparisons | Subjects, criteria, recommendations |
| news | Current events | Facts, context, perspectives |
| vlog | Daily content | Scenes, notable points |
| general | Fallback | Core content, key points, analysis |

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/summarize` | POST | Submit video for summarization |
| `/api/summarize/batch` | POST | Batch submit |
| `/api/tasks` | GET | List tasks |
| `/api/tasks/{id}` | GET | Task detail |
| `/api/tasks/{id}/status` | GET | Lightweight status polling |
| `/api/tasks/{id}/stream` | GET | SSE streaming output |
| `/api/storage` | GET | Storage info |
| `/api/storage` | DELETE | Cleanup data |

## Configuration

Environment variables (`.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | | OpenAI/MIMO API key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API endpoint |
| `OPENAI_MODEL` | `gpt-4o` | Text model |
| `OPENAI_VISION_MODEL` | | Vision model for multimodal |
| `ANTHROPIC_API_KEY` | | Claude API key |
| `WHISPER_MODEL` | `base` | Whisper model size |
| `MAX_FRAMES` | `10` | Max frames for multimodal |

## Tech Stack

- Python 3.10+, FastAPI, uv
- Whisper (ASR), yt-dlp (download), ffmpeg (audio/video processing)
- Claude / OpenAI-compatible LLMs
- SQLite (WAL mode)

## License

MIT License
