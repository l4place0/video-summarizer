# INSTALL.md — Agent Setup Guide

This document is for AI agents (Claude Code, etc.) to set up the bilibili-learning-helper project.

## Prerequisites

Check before proceeding:

```bash
python3 --version    # Need 3.10+
ffmpeg -version      # Need ffmpeg installed
```

If ffmpeg is missing:
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: download from https://ffmpeg.org and add to PATH

## Setup

```bash
cd /home/l4p/project-v

# Install uv if not present
pip install uv 2>/dev/null || pip3 install uv 2>/dev/null

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with real API keys:
#   OPENAI_API_KEY=...
#   OPENAI_BASE_URL=...
#   OPENAI_MODEL=...
#   OPENAI_VISION_MODEL=...  (for multimodal, e.g. mimo-v2-omni)
#   ANTHROPIC_API_KEY=...
```

## Start Service

```bash
cd /home/l4p/project-v

# Development (with hot-reload)
bash scripts/dev.sh

# Or manually
uv run uvicorn core.main:app --host 0.0.0.0 --port 8000
```

Verify:
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"0.1.0"}
```

## Use Skill

```bash
# Basic summary
bash skill/scripts/summarize.sh "https://bilibili.com/video/BVxxxxx"

# With options
bash skill/scripts/summarize.sh "https://bilibili.com/video/BVxxxxx" \
  --lang zh --provider openai --detail normal --mode audio

# Multimodal (video frames + transcript)
bash skill/scripts/summarize.sh "https://bilibili.com/video/BVxxxxx" \
  --mode multimodal --provider openai

# Check status
bash skill/scripts/status.sh

# Cleanup storage
bash skill/scripts/status.sh --cleanup
```

## Web UI

After starting the service, open `http://localhost:8000` in a browser.

## Troubleshooting

- "Service not running" → Start the uvicorn service first
- Bilibili 403 → Need valid `data/cookies.txt` (Netscape format)
- Whisper slow → First run downloads the model (~140MB for "base")
- Multimodal 404 → Check `OPENAI_VISION_MODEL` supports image input
